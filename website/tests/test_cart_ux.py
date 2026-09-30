"""Mini-cart / cart page AJAX: JSON payloads, totals with discount, capped quantity,
formatting, empty states."""

from website.cart import format_rub, plural_items
from website.models import ProductSizeStock

from .test_product_page import ServedProductBase

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class CartJsonTests(ServedProductBase):
    def setUp(self):
        super().setUp()
        self.product.old_price = "2000"
        self.product.save()

    def add(self, size="M"):
        return self.client.post(f"/cart/add/{self.product.id}/", {"size": size}, **AJAX).json()

    def test_add_returns_item_with_size_price_and_summary(self):
        data = self.add()
        item = data["item"]
        self.assertEqual(item["size"], "M")
        self.assertEqual(item["quantity"], 1)
        self.assertEqual(item["price_display"], "1 500 ₽")
        self.assertEqual(item["old_price_display"], "2 000 ₽")
        self.assertEqual(item["technique"], "Печать")
        self.assertEqual(data["summary"]["count_label"], "1 товар")
        self.assertEqual(data["summary"]["discount"], 500)
        self.assertFalse(data["capped"])

    def test_same_variant_merges_and_caps_at_stock(self):
        ProductSizeStock.objects.filter(page=self.product, size="M").update(quantity=2)
        self.add()
        second = self.add()
        self.assertEqual(second["item"]["quantity"], 2)  # одна позиция, количество 2
        third = self.add()
        self.assertTrue(third["capped"])
        self.assertEqual(third["item"]["quantity"], 2)
        self.assertEqual(len(self.client.session["cart"]), 1)

    def test_update_quantity_recalculates_line_and_totals(self):
        self.add()
        data = self.client.post(f"/cart/update/{self.product.id}/M/", {"quantity": 3}, **AJAX).json()
        self.assertEqual(data["item"]["quantity"], 3)
        self.assertEqual(data["item"]["subtotal_display"], "4 500 ₽")
        self.assertEqual(data["summary"]["count_label"], "3 товара")
        self.assertEqual(data["summary"]["total"], 4500)
        self.assertEqual(data["summary"]["full_total"], 6000)
        self.assertEqual(data["cart_count"], 3)

    def test_update_is_capped_by_stock(self):
        self.add()
        data = self.client.post(f"/cart/update/{self.product.id}/M/", {"quantity": 99}, **AJAX).json()
        self.assertEqual(data["item"]["quantity"], 5)

    def test_remove_returns_empty_summary(self):
        self.add()
        data = self.client.post(f"/cart/remove/{self.product.id}/M/", **AJAX).json()
        self.assertEqual(data["summary"]["count"], 0)
        self.assertIsNone(data["item"])

    def test_error_is_json_for_unavailable_size(self):
        response = self.client.post(f"/cart/add/{self.product.id}/", {"size": "XL"}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Выберите доступный размер")


class CartPageRenderTests(ServedProductBase):
    def test_cart_page_has_summary_size_and_no_update_button(self):
        self.client.post(f"/cart/add/{self.product.id}/", {"size": "M"}, **AJAX)
        response = self.client.get("/cart/")
        self.assertContains(response, "Ваш заказ")
        self.assertContains(response, "Размер: <strong>M</strong>", html=False)
        self.assertNotContains(response, "Обновить")
        self.assertContains(response, "data-summary-discount-row hidden")  # скидки нет — строка скрыта
        self.assertContains(response, "В избранное")

    def test_empty_cart_and_favorites_states(self):
        self.assertContains(self.client.get("/cart/"), "Корзина пока пуста")
        self.assertContains(self.client.get("/favorites/"), "В избранном пока ничего нет")

    def test_mini_cart_and_toast_region_on_every_page(self):
        response = self.client.get(self.product.url)
        self.assertContains(response, "data-mini-cart")
        self.assertContains(response, 'data-toast-region aria-live="polite"')


class FormattingTests(ServedProductBase):
    def test_rub_and_plural(self):
        self.assertEqual(format_rub(14400), "14 400 ₽")
        self.assertEqual([plural_items(n) for n in (1, 2, 5, 11, 21, 22)],
                         ["1 товар", "2 товара", "5 товаров", "11 товаров", "21 товар", "22 товара"])
