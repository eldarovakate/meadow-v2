"""
Payment flow tests for the YooKassa (ЮKassa) integration.

No real HTTP calls are made to YooKassa, and the `yookassa` package itself
is never faked or replaced in sys.modules. The only integration boundary is
`website.payments.yookassa_client` (a `YooKassaClient` instance) — tests
patch that single object, so the real SDK's actual presence/absence on the
machine is irrelevant to whether these tests can run.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from wagtail.models import Page

from website.models import CatalogPage, Order, OrderItem, ProductPage, ProductSizeStock
from website.payments import create_order_payment, process_webhook_event, sync_order_payment
from website.stock import InsufficientStockError, reserve_stock_for_lines

User = get_user_model()


def make_payment(payment_id, status, value, currency="RUB", order_id=None, metadata=None):
    if metadata is None:
        metadata = {"order_id": str(order_id)} if order_id is not None else {}
    return SimpleNamespace(
        id=payment_id,
        status=status,
        amount=SimpleNamespace(value=value, currency=currency),
        metadata=metadata,
        confirmation=SimpleNamespace(confirmation_url="https://yookassa.ru/pay/fake"),
    )


@override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
class PaymentTestBase(TestCase):
    """No real network calls: YooKassa client is mocked per-test, Telegram notifications are disabled here."""

    def setUp(self):
        root = Page.objects.get(id=1)
        self.catalog = CatalogPage(title="Catalog", slug="catalog-test")
        root.add_child(instance=self.catalog)

        self.product = ProductPage(title="Test Product", slug="test-product", price="1500")
        self.catalog.add_child(instance=self.product)
        ProductSizeStock.objects.create(page=self.product, size="M", quantity=5)

        self.user = User.objects.create_user(username="buyer", password="pw12345!", email="buyer@example.com")
        self.other_user = User.objects.create_user(username="other", password="pw12345!", email="other@example.com")

    def make_order(self, user=None, total=1500, reserve=True, quantity=1):
        order = Order.objects.create(
            user=user or self.user,
            total=total,
            full_name="Test Buyer",
            phone="+79990000000",
            email="buyer@example.com",
            city="Moscow",
            street="Test st.",
            house="1",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            size="M",
            quantity=quantity,
            unit_price=1500,
        )
        if reserve:
            stock = ProductSizeStock.objects.get(page=self.product, size="M")
            stock.quantity -= quantity
            stock.save(update_fields=["quantity"])
        return order


class PaymentCreationTests(PaymentTestBase):
    """A. Payment creation."""

    @patch("website.payments.yookassa_client")
    def test_create_order_payment_uses_order_total_rub_capture_and_metadata(self, mock_client):
        order = self.make_order(total=1500)
        mock_client.create_payment.return_value = make_payment("pay_1", "pending", "1500.00", order_id=order.id)

        url = create_order_payment(order, "https://meadowshore.ru/checkout/success/%d/" % order.id)

        self.assertEqual(url, "https://yookassa.ru/pay/fake")
        payload, idempotence_key = mock_client.create_payment.call_args.args
        self.assertEqual(payload["amount"], {"value": "1500.00", "currency": "RUB"})
        self.assertTrue(payload["capture"])
        self.assertEqual(payload["confirmation"]["type"], "redirect")
        self.assertEqual(payload["metadata"], {"order_id": str(order.id)})
        self.assertNotIn("receipt", payload)
        self.assertTrue(idempotence_key)

        order.refresh_from_db()
        self.assertEqual(order.payment_id, "pay_1")

    @patch("website.payments.yookassa_client")
    def test_idempotence_key_stable_across_retry_after_network_error(self, mock_client):
        order = self.make_order(total=1500)

        mock_client.create_payment.side_effect = ConnectionError("network timeout")
        with self.assertRaises(ConnectionError):
            create_order_payment(order, "https://meadowshore.ru/return/")

        order.refresh_from_db()
        first_key = order.payment_idempotence_key
        self.assertTrue(first_key)

        mock_client.create_payment.side_effect = None
        mock_client.create_payment.return_value = make_payment("pay_1", "pending", "1500.00", order_id=order.id)
        create_order_payment(order, "https://meadowshore.ru/return/")

        used_keys = [call.args[1] for call in mock_client.create_payment.call_args_list]
        self.assertEqual(used_keys[0], used_keys[1])
        self.assertEqual(used_keys[0], first_key)


class WebhookSyncTests(PaymentTestBase):
    """B-I. Webhook verification, spoofing, mismatch, and idempotency."""

    def _webhook_body(self, payment_id, event="payment.succeeded"):
        return json.dumps({"event": event, "object": {"id": payment_id}}).encode()

    @patch("website.payments.yookassa_client")
    def test_valid_succeeded_webhook_marks_order_paid(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_ok"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment("pay_ok", "succeeded", "1500.00", order_id=order.id)

        process_webhook_event(self._webhook_body("pay_ok"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)

    @patch("website.payments.yookassa_client")
    def test_spoofed_webhook_status_ignored_real_api_says_pending(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_spoof"
        order.save(update_fields=["payment_id"])
        # Webhook JSON claims "succeeded" but the verified API object says pending.
        mock_client.find_payment.return_value = make_payment("pay_spoof", "pending", "1500.00", order_id=order.id)

        process_webhook_event(self._webhook_body("pay_spoof", event="payment.succeeded"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    @patch("website.payments.yookassa_client")
    def test_wrong_amount_does_not_mark_paid(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_amt"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment("pay_amt", "succeeded", "999.00", order_id=order.id)

        process_webhook_event(self._webhook_body("pay_amt"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    @patch("website.payments.yookassa_client")
    def test_wrong_currency_does_not_mark_paid(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_cur"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment(
            "pay_cur", "succeeded", "1500.00", currency="USD", order_id=order.id
        )

        process_webhook_event(self._webhook_body("pay_cur"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    @patch("website.payments.yookassa_client")
    def test_wrong_payment_order_relation_does_not_mark_paid(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_rel"
        order.save(update_fields=["payment_id"])
        other_order = self.make_order(total=1500, reserve=False)
        # Verified payment matches order's payment_id/amount/currency, but its metadata
        # points at a different order — must not be trusted.
        mock_client.find_payment.return_value = make_payment(
            "pay_rel", "succeeded", "1500.00", order_id=other_order.id
        )

        process_webhook_event(self._webhook_body("pay_rel"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    @patch("website.notifications.send_payment_confirmed_notification")
    @patch("website.payments.yookassa_client")
    def test_duplicate_succeeded_webhook_does_not_repeat_side_effects(self, mock_client, mock_notify):
        order = self.make_order(total=1500)
        order.payment_id = "pay_dup"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment("pay_dup", "succeeded", "1500.00", order_id=order.id)

        with self.captureOnCommitCallbacks(execute=True):
            process_webhook_event(self._webhook_body("pay_dup"))
            process_webhook_event(self._webhook_body("pay_dup"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(mock_notify.call_count, 1)

    @patch("website.payments.yookassa_client")
    def test_canceled_payment_restores_stock_once(self, mock_client):
        order = self.make_order(total=1500, quantity=2)
        order.payment_id = "pay_cancel"
        order.save(update_fields=["payment_id"])
        stock_before = ProductSizeStock.objects.get(page=self.product, size="M").quantity

        mock_client.find_payment.return_value = make_payment("pay_cancel", "canceled", "1500.00", order_id=order.id)
        process_webhook_event(self._webhook_body("pay_cancel", event="payment.canceled"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        stock_after = ProductSizeStock.objects.get(page=self.product, size="M").quantity
        self.assertEqual(stock_after, stock_before + 2)

    @patch("website.payments.yookassa_client")
    def test_duplicate_canceled_webhook_does_not_restore_stock_twice(self, mock_client):
        order = self.make_order(total=1500, quantity=2)
        order.payment_id = "pay_dupcancel"
        order.save(update_fields=["payment_id"])

        mock_client.find_payment.return_value = make_payment(
            "pay_dupcancel", "canceled", "1500.00", order_id=order.id
        )
        process_webhook_event(self._webhook_body("pay_dupcancel", event="payment.canceled"))
        stock_after_first = ProductSizeStock.objects.get(page=self.product, size="M").quantity

        process_webhook_event(self._webhook_body("pay_dupcancel", event="payment.canceled"))
        stock_after_second = ProductSizeStock.objects.get(page=self.product, size="M").quantity

        self.assertEqual(stock_after_first, stock_after_second)

    def test_malformed_json_raises(self):
        from website.payments import WebhookMalformed

        with self.assertRaises(WebhookMalformed):
            process_webhook_event(b"{not json")

    @patch("website.payments.yookassa_client")
    def test_unknown_event_is_ignored_without_error(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_unknown"
        order.save(update_fields=["payment_id"])

        process_webhook_event(json.dumps({"event": "refund.succeeded", "object": {"id": "pay_unknown"}}).encode())

        mock_client.find_payment.assert_not_called()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)


class ReturnUrlTests(PaymentTestBase):
    """J-M. Return URL sync behaviour and order ownership."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")

    @patch("website.payments.yookassa_client")
    def test_return_url_succeeded_syncs_order_to_paid(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_ret_ok"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment(
            "pay_ret_ok", "succeeded", "1500.00", order_id=order.id
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.get(f"/checkout/success/{order.id}/")

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(response.status_code, 200)

    @patch("website.payments.yookassa_client")
    def test_return_url_pending_does_not_mark_paid(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_ret_pending"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment(
            "pay_ret_pending", "pending", "1500.00", order_id=order.id
        )

        response = self.client.get(f"/checkout/success/{order.id}/")

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)
        self.assertEqual(response.context["payment_state"], "pending")

    @patch("website.payments.yookassa_client")
    def test_return_url_canceled_shows_cancelled_state(self, mock_client):
        order = self.make_order(total=1500)
        order.payment_id = "pay_ret_cancel"
        order.save(update_fields=["payment_id"])
        mock_client.find_payment.return_value = make_payment(
            "pay_ret_cancel", "canceled", "1500.00", order_id=order.id
        )

        response = self.client.get(f"/checkout/success/{order.id}/")

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(response.context["payment_state"], "cancelled")

    def test_other_user_cannot_view_order(self):
        order = self.make_order(user=self.other_user, reserve=False)

        response = self.client.get(f"/checkout/success/{order.id}/")

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        order = self.make_order(reserve=False)

        response = self.client.get(f"/checkout/success/{order.id}/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/account/login/", response.url)


class CheckoutViewTests(PaymentTestBase):
    """N. Payment.create failure during checkout does not leave a false success / lost stock."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")
        session = self.client.session
        session["cart"] = {f"{self.product.id}:M": 1}
        session.save()

    def _checkout_payload(self):
        return {
            "full_name": "Test Buyer",
            "phone": "+79990000000",
            "email": "buyer@example.com",
            "city": "Moscow",
            "street": "Test st.",
            "house": "1",
            "postal_code": "",
            "comment": "",
        }

    @patch("website.payments.yookassa_client")
    def test_payment_create_failure_cancels_order_and_restores_stock(self, mock_client):
        stock_before = ProductSizeStock.objects.get(page=self.product, size="M").quantity
        mock_client.create_payment.side_effect = ConnectionError("boom")

        response = self.client.post("/checkout/", data=self._checkout_payload(), follow=True)

        order = Order.objects.latest("created_at")
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(response.context["payment_state"], "create_failed")

        stock_after = ProductSizeStock.objects.get(page=self.product, size="M").quantity
        self.assertEqual(stock_before, stock_after)

    @patch("website.payments.yookassa_client")
    def test_successful_checkout_reserves_stock_and_redirects_to_payment(self, mock_client):
        mock_client.create_payment.return_value = make_payment("pay_new", "pending", "1500.00", order_id=999999)
        stock_before = ProductSizeStock.objects.get(page=self.product, size="M").quantity

        response = self.client.post("/checkout/", data=self._checkout_payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://yookassa.ru/pay/fake")
        stock_after = ProductSizeStock.objects.get(page=self.product, size="M").quantity
        self.assertEqual(stock_after, stock_before - 1)

    def test_insufficient_stock_blocks_checkout_without_creating_order(self):
        session = self.client.session
        session["cart"] = {f"{self.product.id}:M": 999}
        session.save()
        orders_before = Order.objects.count()

        response = self.client.post("/checkout/", data=self._checkout_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), orders_before)

    @patch("website.payments.yookassa_client")
    def test_retry_after_create_timeout_reuses_same_idempotence_key(self, mock_client):
        """
        Пользовательский flow: Payment.create падает по таймауту (исход на
        стороне ЮKassa неизвестен) -> заказ CANCELLED -> пользователь жмёт
        Retry -> повторный Payment.create ДОЛЖЕН получить тот же ключ, чтобы
        не создать дублирующий платёж, если первый запрос всё же дошёл.
        """
        mock_client.create_payment.side_effect = ConnectionError("timeout")

        self.client.post("/checkout/", data=self._checkout_payload())

        order = Order.objects.latest("created_at")
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(order.payment_id, "")
        first_key = order.payment_idempotence_key
        self.assertTrue(first_key)

        mock_client.create_payment.side_effect = None
        mock_client.create_payment.return_value = make_payment(
            "pay_retry_ok", "pending", "1500.00", order_id=order.id
        )

        retry_response = self.client.post(f"/checkout/success/{order.id}/retry/")

        order.refresh_from_db()
        self.assertEqual(retry_response.status_code, 302)
        self.assertEqual(order.payment_id, "pay_retry_ok")
        self.assertEqual(order.payment_idempotence_key, first_key)

        used_keys = [call.args[1] for call in mock_client.create_payment.call_args_list]
        self.assertEqual(used_keys, [first_key, first_key])


class StockReservationTests(PaymentTestBase):
    def test_reserve_stock_for_lines_raises_when_insufficient(self):
        lines = [{"product": self.product, "size": "M", "quantity": 999}]
        stock_before = ProductSizeStock.objects.get(page=self.product, size="M").quantity

        with self.assertRaises(InsufficientStockError):
            reserve_stock_for_lines(lines)

        stock_after = ProductSizeStock.objects.get(page=self.product, size="M").quantity
        self.assertEqual(stock_before, stock_after)


class RetryPaymentTests(PaymentTestBase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")

    @patch("website.payments.yookassa_client")
    def test_retry_after_confirmed_cancellation_gets_new_idempotence_key(self, mock_client):
        """
        Пользовательский flow: заказ имел реальный payment_id, ЮKassa
        достоверно (через Payment.find_one) подтвердила canceled -> заказ
        CANCELLED -> Retry ДОЛЖЕН получить НОВЫЙ Idempotence-Key — это
        независимая новая попытка оплаты, не повтор старой.
        """
        order = self.make_order(total=1500, quantity=1)
        order.payment_id = "pay_orig"
        order.payment_idempotence_key = "orig-key"
        order.save(update_fields=["payment_id", "payment_idempotence_key"])

        mock_client.find_payment.return_value = make_payment("pay_orig", "canceled", "1500.00", order_id=order.id)
        order, _payment = sync_order_payment(order)
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(order.payment_id, "pay_orig")  # confirmed-cancel не сбрасывает payment_id сам по себе

        stock_before = ProductSizeStock.objects.get(page=self.product, size="M").quantity

        mock_client.create_payment.return_value = make_payment("pay_new", "pending", "1500.00", order_id=order.id)
        response = self.client.post(f"/checkout/success/{order.id}/retry/")

        order.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(order.payment_id, "pay_new")
        self.assertNotEqual(order.payment_idempotence_key, "orig-key")
        stock_after = ProductSizeStock.objects.get(page=self.product, size="M").quantity
        self.assertEqual(stock_after, stock_before - 1)

    def test_retry_blocked_when_order_not_cancelled(self):
        order = self.make_order(total=1500)  # status stays NEW, no payment_id

        self.client.post(f"/checkout/success/{order.id}/retry/", follow=True)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)
        self.assertEqual(order.payment_id, "")

    def test_retry_requires_ownership(self):
        order = self.make_order(user=self.other_user, reserve=False)
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])

        response = self.client.post(f"/checkout/success/{order.id}/retry/")

        self.assertEqual(response.status_code, 404)
