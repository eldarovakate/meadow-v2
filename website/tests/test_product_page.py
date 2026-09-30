"""Product page redesign: consistent purchase state, size buttons, data-driven blocks
that hide when data is missing, recommendations, and the add/remove cart toggle."""

from django.core.cache import cache
from django.test import Client, override_settings
from wagtail.models import Site

from website.models import ProductPage, ProductSizeStock
from website.product_facts import care_items, parse_composition, parse_density, parse_fabric

from .test_payments import PaymentTestBase

FABRIC = (
    "Плотный и мягкий трикотаж плотностью 240 г/м².\n"
    "Состав: 95% хлопок, 5% лайкра.\n"
    "Характеристики ткани: футер 2х-нитка."
)


class ProductFactsParsingTests(PaymentTestBase):
    def test_parses_only_what_is_in_the_text(self):
        self.assertEqual(parse_composition(FABRIC), "95% хлопок, 5% лайкра")
        self.assertEqual(parse_density(FABRIC), "240 г/м²")
        self.assertEqual(parse_fabric(FABRIC), "футер 2х-нитка")
        self.assertEqual(parse_composition("Мягкая ткань"), "")
        self.assertEqual(parse_density(""), "")

    def test_care_items_split_by_lines_sentences_or_commas(self):
        self.assertEqual(care_items("Стирать при 30 °C.\nНе отбеливать."), ["Стирать при 30 °C", "Не отбеливать"])
        self.assertEqual(care_items("Стирать при 30 °C. Не отбеливать."), ["Стирать при 30 °C", "Не отбеливать"])
        self.assertEqual(
            care_items("Вывернуть изделие, стирка при 30°C, не сушить в машинке"),
            ["Вывернуть изделие", "Стирка при 30°C", "Не сушить в машинке"],
        )
        self.assertEqual(care_items(""), [])


class ServedProductBase(PaymentTestBase):
    """Каталог базового теста лежит вне корня сайта — переносим его под корень, чтобы страница открывалась."""

    def setUp(self):
        super().setUp()
        cache.clear()  # Wagtail кэширует корневые пути сайтов между тестами
        self.catalog.move(Site.objects.get(is_default_site=True).root_page, pos="last-child")
        self.catalog.refresh_from_db()
        self.product.refresh_from_db()
        self.client = Client()


@override_settings(SALES_MODE="sales")
class ProductPageRenderTests(ServedProductBase):
    def setUp(self):
        super().setUp()
        self.product.collection_name = "Лесные жители"
        self.product.fabric_info = FABRIC
        self.product.care_info = "Стирать при 30 °C. Не отбеливать."
        self.product.save()
        ProductSizeStock.objects.create(page=self.product, size="S", quantity=0)
        ProductSizeStock.objects.create(page=self.product, size="L", quantity=2)

    def get(self):
        return self.client.get(self.product.url)

    def test_single_h1_breadcrumbs_and_no_sku_near_title(self):
        response = self.get()
        html = response.content.decode()
        self.assertEqual(html.count("<h1"), 1)
        self.assertContains(response, 'aria-current="page">Test Product</li>', html=False)
        # артикул только в характеристиках, не в шапке карточки
        self.assertNotContains(response, "product-detail__sku")
        self.assertContains(response, "MS-")

    def test_sizes_are_buttons_with_disabled_and_low_stock(self):
        response = self.get()
        self.assertNotContains(response, "<select")
        self.assertContains(response, 'value="S" class="size-option__input" disabled')
        self.assertContains(response, "осталось 2")
        self.assertContains(response, "Таблица размеров")

    def test_quick_specs_and_characteristics_come_from_existing_fields(self):
        response = self.get()
        self.assertContains(response, "95% хлопок, 5% лайкра · 240 г/м² · печать")
        self.assertContains(response, "<dt>Полотно</dt>")
        self.assertNotContains(response, "<dt>Посадка</dt>")  # нет данных — нет строки
        self.assertNotContains(response, "Производство")

    def test_available_state_in_sales_mode(self):
        response = self.get()
        self.assertEqual(response.context["purchase_state"], "available")
        self.assertContains(response, "В наличии")
        self.assertContains(response, "Добавить в корзину")
        self.assertNotContains(response, "Добавить в предзаказ")

    @override_settings(SALES_MODE="preorder")
    def test_preorder_state_has_no_contradiction(self):
        response = self.get()
        self.assertEqual(response.context["purchase_state"], "preorder")
        self.assertContains(response, "Предзаказ")
        self.assertContains(response, "Добавить в предзаказ")
        self.assertContains(response, "Отправка заказов начнётся с")
        self.assertNotContains(response, "В наличии")

    def test_sold_out_when_all_sizes_empty(self):
        ProductSizeStock.objects.filter(page=self.product).update(quantity=0)
        response = self.get()
        self.assertEqual(response.context["purchase_state"], "sold_out")
        self.assertNotContains(response, 'id="add-to-cart"')

    def test_blocks_without_data_are_hidden(self):
        response = self.get()
        self.assertNotContains(response, 'id="posadka"')          # нет fit_notes / модели
        self.assertNotContains(response, "На модели")
        self.assertNotContains(response, 'id="istoriya-printa"')  # нет body
        self.assertNotContains(response, "Отзывы")

    def test_fit_and_model_blocks_shown_when_filled(self):
        self.product.fit_notes = "Свободная посадка\nСпущенное плечо"
        self.product.model_size = "M"
        self.product.model_height = 174
        self.product.save()
        response = self.get()
        self.assertContains(response, 'id="posadka"')
        self.assertContains(response, "На модели размер M · рост 174 см")
        self.assertContains(response, "240 г/м² · свободная посадка · печать")

    def test_related_products_exclude_current_and_stay_in_collection(self):
        same = ProductPage(title="Same", slug="same", price="1500", collection_name="Лесные жители")
        other = ProductPage(title="Other", slug="other", price="1500", collection_name="Другая")
        self.catalog.add_child(instance=same)
        self.catalog.add_child(instance=other)
        related = self.get().context["related_products"]
        self.assertEqual([p.id for p in related], [same.id])


class CartToggleTests(ServedProductBase):

    def test_page_knows_which_sizes_are_in_cart_and_ajax_remove_updates_count(self):
        self.client.post(f"/cart/add/{self.product.id}/", {"size": "M"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(self.client.get(self.product.url).context["in_cart_sizes"], ["M"])

        response = self.client.post(f"/cart/remove/{self.product.id}/M/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["cart_count"], 0)
        self.assertEqual(data["summary"]["total"], 0)
        self.assertEqual(self.client.get(self.product.url).context["in_cart_sizes"], [])


class ProductPageExtraBlocksTests(ServedProductBase):
    """Блоки главной, которые владелец ставит внизу страницы товара через Настройки."""

    def _settings(self):
        from website.models import SiteSettings
        return SiteSettings.for_site(Site.objects.get(is_default_site=True))

    def test_blocks_from_settings_render_on_product_page(self):
        site_settings = self._settings()
        site_settings.product_page_blocks = [("collection_statement", {
            "is_visible": True, "eyebrow": "Визуальный дневник", "title": "По дороге",
            "meta": "", "body": "Цвет, фактура", "images": [], "cta_text": "", "cta_url": "",
        })]
        site_settings.save()
        response = self.client.get(self.product.url)
        self.assertContains(response, "product-extra-blocks")
        self.assertContains(response, "По дороге")

    def test_empty_setting_renders_nothing(self):
        site_settings = self._settings()
        site_settings.product_page_blocks = []
        site_settings.save()
        self.assertNotContains(self.client.get(self.product.url), "product-extra-blocks")

    def test_admin_settings_form_opens(self):
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw12345!")
        self.client.force_login(admin)
        site = Site.objects.get(is_default_site=True)
        response = self.client.get(f"/admin/settings/website/sitesettings/{site.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Блоки внизу страницы товара")
