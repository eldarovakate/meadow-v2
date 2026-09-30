"""
Pre-launch hardening: server-side stock/size checks (O1), pending return with
«Перейти к оплате» (O2), YooKassa request timeout (O3), double-POST protection (A2),
phone validation (A8), sellable-product check on add-to-cart (A11), notification
wording (B3) and password-reset URL independent of the Host header (A10).
"""

from unittest.mock import patch

from django.core import mail
from django.db import IntegrityError, transaction
from django.test import Client, override_settings

from website.forms import normalize_phone
from website.models import Order, ProductPage, ProductSizeStock
from website.notifications import send_order_notifications, send_payment_confirmed_notification
from website.payments import process_webhook_event

from .test_payments import PaymentTestBase, User, make_payment


def checkout_payload(**overrides):
    data = {
        "full_name": "Test Buyer",
        "phone": "+79990000000",
        "email": "buyer@example.com",
        "city": "Moscow",
        "street": "Test st.",
        "house": "1",
        "postal_code": "",
        "comment": "",
    }
    data.update(overrides)
    return data


class LoggedInBase(PaymentTestBase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")

    def set_cart(self, cart):
        session = self.client.session
        session["cart"] = cart
        session.save()

    def stock_m(self):
        return ProductSizeStock.objects.get(page=self.product, size="M").quantity


class ServerSideStockTests(LoggedInBase):
    """O1: checkout never trusts the session cart."""

    def assert_rejected(self, cart):
        self.set_cart(cart)
        stock_before = self.stock_m()
        orders_before = Order.objects.count()

        with patch("website.payments.yookassa_client") as mock_client:
            response = self.client.post("/checkout/", data=checkout_payload())
            mock_client.create_payment.assert_not_called()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), orders_before)
        self.assertEqual(self.stock_m(), stock_before)

    def test_missing_size_rejected(self):
        self.assert_rejected({f"{self.product.id}:-": 1})

    def test_nonexistent_size_rejected(self):
        self.assert_rejected({f"{self.product.id}:XXL": 1})

    def test_zero_quantity_rejected(self):
        self.assert_rejected({f"{self.product.id}:M": 0})

    def test_negative_quantity_rejected(self):
        self.assert_rejected({f"{self.product.id}:M": -3})

    def test_quantity_over_stock_rejected(self):
        self.assert_rejected({f"{self.product.id}:M": 6})

    def test_sold_out_product_rejected_at_checkout(self):
        self.product.status = ProductPage.SOLD_OUT
        self.product.save()
        self.assert_rejected({f"{self.product.id}:M": 1})

    @patch("website.payments.yookassa_client")
    def test_normal_purchase_of_existing_size(self, mock_client):
        mock_client.create_payment.return_value = make_payment("pay_ok", "pending", "3000.00", order_id=1)
        self.set_cart({f"{self.product.id}:M": 2})

        response = self.client.post("/checkout/", data=checkout_payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://yookassa.ru/pay/fake")
        order = Order.objects.get()
        self.assertEqual(order.total, 3000)
        self.assertEqual(order.items.get().size, "M")
        self.assertEqual(self.stock_m(), 3)

    def test_cart_update_cannot_create_sizeless_line(self):
        """The old bypass: /cart/update/<id>/-/ used to add a size-less line with any quantity."""
        self.set_cart({})
        self.client.post(f"/cart/update/{self.product.id}/-/", data={"quantity": 50})
        self.assertEqual(self.client.session.get("cart"), {})


class CartAddAvailabilityTests(LoggedInBase):
    """A11: only live, «В наличии», priced products go into the cart."""

    def add(self, **post):
        return self.client.post(
            f"/cart/add/{self.product.id}/",
            data={"size": "M", **post},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_available_product_added(self):
        response = self.add()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["cart"], {f"{self.product.id}:M": 1})

    def test_sold_out_status_rejected_even_with_stock(self):
        self.product.status = ProductPage.SOLD_OUT
        self.product.save()
        self.assertEqual(self.add().status_code, 400)
        self.assertFalse(self.client.session.get("cart"))

    def test_coming_soon_rejected(self):
        self.product.status = ProductPage.COMING_SOON
        self.product.save()
        self.assertEqual(self.add().status_code, 400)

    def test_unpublished_rejected(self):
        self.product.unpublish()
        self.assertEqual(self.add().status_code, 400)

    def test_product_without_price_rejected(self):
        self.product.price = ""
        self.product.save()
        self.assertEqual(self.add().status_code, 400)


class PendingReturnTests(LoggedInBase):
    """O2: returning from ЮKassa without paying → same order, same payment, no new stock hit."""

    @patch("website.payments.yookassa_client")
    def test_create_leave_return_pay_again_same_order(self, mock_client):
        self.set_cart({f"{self.product.id}:M": 1})
        stock_before = self.stock_m()

        # 1. создать заказ → уход в ЮKassa
        mock_client.create_payment.return_value = make_payment("pay_same", "pending", "1500.00", order_id=0)
        response = self.client.post("/checkout/", data=checkout_payload())
        self.assertEqual(response.url, "https://yookassa.ru/pay/fake")
        order = Order.objects.get()
        self.assertEqual(self.stock_m(), stock_before - 1)

        # 2. вернуться без оплаты: статус + кнопка на confirmation_url того же платежа
        mock_client.find_payment.return_value = make_payment("pay_same", "pending", "1500.00", order_id=order.id)
        page = self.client.get(f"/checkout/success/{order.id}/")
        self.assertEqual(page.context["payment_state"], "pending")
        self.assertEqual(page.context["payment_url"], "https://yookassa.ru/pay/fake")
        self.assertContains(page, "Заказ ожидает оплаты")
        self.assertContains(page, "Перейти к оплате")
        self.assertContains(page, 'href="https://yookassa.ru/pay/fake"')

        # повторный заход на страницу ничего не создаёт и не списывает
        self.client.get(f"/checkout/success/{order.id}/")
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(mock_client.create_payment.call_count, 1)
        self.assertEqual(self.stock_m(), stock_before - 1)

        # 3. оплатить тот же заказ
        mock_client.find_payment.return_value = make_payment("pay_same", "succeeded", "1500.00", order_id=order.id)
        with self.captureOnCommitCallbacks(execute=True):
            process_webhook_event(f'{{"event": "payment.succeeded", "object": {{"id": "pay_same"}}}}')

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.stock_m(), stock_before - 1)
        page = self.client.get(f"/checkout/success/{order.id}/")
        self.assertEqual(page.context["payment_state"], "paid")

    def test_pending_without_payment_yet_shows_no_pay_button(self):
        order = self.make_order()
        page = self.client.get(f"/checkout/success/{order.id}/")
        self.assertEqual(page.context["payment_state"], "pending")
        self.assertIsNone(page.context["payment_url"])


class DoubleSubmitTests(LoggedInBase):
    """A2: the same checkout form posted twice creates one order and reserves once."""

    @patch("website.payments.yookassa_client")
    def test_repeated_post_with_same_token_creates_one_order(self, mock_client):
        mock_client.create_payment.return_value = make_payment("pay_dbl", "pending", "1500.00", order_id=0)
        self.set_cart({f"{self.product.id}:M": 1})
        stock_before = self.stock_m()
        payload = checkout_payload(checkout_token="tok-123")

        first = self.client.post("/checkout/", data=payload)
        self.set_cart({f"{self.product.id}:M": 1})  # как будто второй запрос прочитал корзину до очистки
        second = self.client.post("/checkout/", data=payload)

        order = Order.objects.get()
        self.assertEqual(first.url, "https://yookassa.ru/pay/fake")
        self.assertRedirects(second, f"/checkout/success/{order.id}/", fetch_redirect_response=False)
        self.assertEqual(self.stock_m(), stock_before - 1)
        self.assertEqual(mock_client.create_payment.call_count, 1)

    def test_token_is_unique_in_db(self):
        """Concurrent case: the second INSERT fails and its transaction (stock reservation included) rolls back."""
        order = self.make_order(reserve=False)
        order.checkout_token = "tok-x"
        order.save(update_fields=["checkout_token"])
        with self.assertRaises(IntegrityError), transaction.atomic():
            Order.objects.create(user=self.user, total=1, full_name="x", phone="+79990000000",
                                 city="c", street="s", house="1", checkout_token="tok-x")

    def test_get_renders_fresh_token(self):
        self.set_cart({f"{self.product.id}:M": 1})
        response = self.client.get("/checkout/")
        self.assertTrue(response.context["form"].initial.get("checkout_token"))
        self.assertContains(response, 'name="checkout_token"')


class PhoneValidationTests(LoggedInBase):
    """A8."""

    def test_russian_variants_normalized(self):
        for raw in ["+7 (999) 123-45-67", "8 999 123 45 67", "79991234567", "9991234567", "+79991234567"]:
            self.assertEqual(normalize_phone(raw), "+79991234567", raw)

    def test_international_plus_accepted(self):
        self.assertEqual(normalize_phone("+375 29 123-45-67"), "+375291234567")

    def test_garbage_rejected(self):
        for raw in ["", "123", "abc", "8 999 123", "+7 999 123 45 67 89"]:
            self.assertIsNone(normalize_phone(raw), raw)

    @patch("website.payments.yookassa_client")
    def test_checkout_stores_normalized_phone_and_rejects_bad_one(self, mock_client):
        mock_client.create_payment.return_value = make_payment("pay_ph", "pending", "1500.00", order_id=0)
        self.set_cart({f"{self.product.id}:M": 1})

        bad = self.client.post("/checkout/", data=checkout_payload(phone="12345"))
        self.assertEqual(bad.status_code, 200)
        self.assertFalse(Order.objects.exists())

        self.client.post("/checkout/", data=checkout_payload(phone="8 (999) 123-45-67"))
        self.assertEqual(Order.objects.get().phone, "+79991234567")


class NotificationWordingTests(PaymentTestBase):
    """B3."""

    def test_created_order_says_awaiting_payment(self):
        order = self.make_order(reserve=False)
        send_order_notifications(order)
        msg = mail.outbox[-1]
        self.assertIn(f"Заказ №{order.id} создан, ожидает оплаты", msg.subject)
        self.assertTrue(msg.body.startswith(f"Заказ №{order.id} создан, ожидает оплаты"))
        self.assertNotIn("оплачен", msg.subject + msg.body)

    def test_payment_confirmed_is_separate(self):
        order = self.make_order(reserve=False)
        send_payment_confirmed_notification(order)
        self.assertTrue(mail.outbox[-1].body.startswith(f"Оплата подтверждена: заказ №{order.id}"))


class YooKassaTimeoutTests(PaymentTestBase):
    """O3: the SDK's HTTP adapter gets a real request timeout."""

    def test_sdk_session_uses_timeout(self):
        from yookassa.client import ApiClient

        from website.payments import yookassa_client

        yookassa_client._configure()
        session = ApiClient().get_session()
        adapter = session.get_adapter("https://api.yookassa.ru/")

        captured = {}

        def fake_send(self_, request, **kwargs):
            captured.update(kwargs)
            raise ConnectionError("stop")

        with patch("requests.adapters.HTTPAdapter.send", fake_send):
            with self.assertRaises(ConnectionError):
                adapter.send(object())
        self.assertEqual(captured["timeout"], (5, 15))


@override_settings(SITE_URL="https://meadowshore.ru")
class PasswordResetHostTests(PaymentTestBase):
    """A10: reset link domain comes from settings, not from the Host header."""

    def test_reset_link_ignores_host_header(self):
        User.objects.filter(pk=self.user.pk).update(email="buyer@example.com")
        with override_settings(ALLOWED_HOSTS=["evil.example", "testserver"]):
            Client().post("/account/password-reset/", data={"email": "buyer@example.com"}, HTTP_HOST="evil.example")
        body = mail.outbox[-1].body
        self.assertIn("https://meadowshore.ru/account/password-reset-confirm/", body)
        self.assertNotIn("evil.example", body)
