"""
Preorder mode tests (SALES_MODE=preorder).

These tests always set SALES_MODE explicitly via override_settings, so they are
decoupled from whatever value happens to be in the local .env. The core guarantee
under test: when SALES_MODE=preorder, checkout (and the payment-retry endpoint)
must never call YooKassa, regardless of request contents — the branch lives in
website.views, gated purely on settings.SALES_MODE.
"""

from unittest.mock import patch

from django.test import Client, override_settings

from website.models import Order
from website.tests.test_payments import PaymentTestBase, make_payment


def _checkout_payload():
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


@override_settings(SALES_MODE="preorder")
class PreorderCheckoutTests(PaymentTestBase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")
        session = self.client.session
        session["cart"] = {f"{self.product.id}:M": 1}
        session.save()

    @patch("website.payments.yookassa_client")
    def test_preorder_checkout_never_calls_yookassa(self, mock_client):
        response = self.client.post("/checkout/", data=_checkout_payload())

        order = Order.objects.latest("created_at")
        self.assertTrue(order.is_preorder)
        self.assertEqual(order.status, Order.STATUS_NEW)
        self.assertEqual(order.payment_id, "")
        mock_client.create_payment.assert_not_called()

        self.assertRedirects(response, f"/checkout/success/{order.id}/")

    def test_preorder_saves_items_contacts_and_total(self):
        self.client.post("/checkout/", data=_checkout_payload())

        order = Order.objects.latest("created_at")
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.full_name, "Test Buyer")
        self.assertEqual(order.phone, "+79990000000")
        self.assertEqual(order.city, "Moscow")
        self.assertEqual(order.street, "Test st.")
        self.assertEqual(order.house, "1")
        self.assertEqual(order.total, 1500)

        item = order.items.get()
        self.assertEqual(item.product_id, self.product.id)
        self.assertEqual(item.size, "M")
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.unit_price, 1500)

    def test_preorder_reserves_stock_like_normal_checkout(self):
        stock_before = self.product.size_stocks.get(size="M").quantity

        self.client.post("/checkout/", data=_checkout_payload())

        stock_after = self.product.size_stocks.get(size="M").quantity
        self.assertEqual(stock_after, stock_before - 1)

    def test_preorder_success_page_shows_preorder_state_and_order_number(self):
        response = self.client.post("/checkout/", data=_checkout_payload(), follow=True)

        self.assertEqual(response.context["payment_state"], "preorder")
        order = response.context["order"]
        self.assertContains(response, "Предзаказ оформлен")
        self.assertContains(response, f"Номер предзаказа: #{order.id}")
        self.assertNotContains(response, "ЮKassa")

    @patch("website.payments.yookassa_client")
    def test_retry_endpoint_never_calls_yookassa_for_a_preorder(self, mock_client):
        """Defense in depth: even a raw POST to the payment-retry URL must not create a YooKassa payment."""
        self.client.post("/checkout/", data=_checkout_payload())
        order = Order.objects.latest("created_at")

        response = self.client.post(f"/checkout/success/{order.id}/retry/")

        mock_client.create_payment.assert_not_called()
        order.refresh_from_db()
        self.assertEqual(order.payment_id, "")
        self.assertRedirects(response, f"/checkout/success/{order.id}/")


@override_settings(SALES_MODE="sales")
class SalesModeStillWorksTests(PaymentTestBase):
    """Switching SALES_MODE back to 'sales' must restore the normal payment flow untouched."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")
        session = self.client.session
        session["cart"] = {f"{self.product.id}:M": 1}
        session.save()

    @patch("website.payments.yookassa_client")
    def test_sales_mode_checkout_still_calls_yookassa_and_redirects_to_payment(self, mock_client):
        mock_client.create_payment.return_value = make_payment("pay_new", "pending", "1500.00", order_id=999999)

        response = self.client.post("/checkout/", data=_checkout_payload())

        order = Order.objects.latest("created_at")
        self.assertFalse(order.is_preorder)
        mock_client.create_payment.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://yookassa.ru/pay/fake")
