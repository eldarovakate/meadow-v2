import re

from django.conf import settings
from django.db import models
from wagtail.models import Orderable, Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.models import Image
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from modelcluster.fields import ParentalKey
from wagtail.contrib.forms.models import AbstractFormField, AbstractEmailForm
from wagtail.contrib.forms.panels import FormSubmissionsPanel

from home.models import (
    EDITORIAL_BLOCKS,
    AboutSectionBlock,
    CollectionSectionBlock,
    FabricSectionBlock,
    HeroSectionBlock,
    ObservationSectionBlock,
    PhilosophySectionBlock,
)

from .cart import get_product_cart_sizes
from .favorites import get_favorite_ids
from .product_facts import (
    SIZE_CHART,
    about_paragraphs,
    care_items,
    parse_composition,
    parse_density,
    parse_fabric,
    split_lines,
)
from .slugs import LatinSlugMixin
from .utils import parse_price_to_int


class AboutPage(LatinSlugMixin, Page):
    body = StreamField([
        ('hero', HeroSectionBlock()),
        ('about', AboutSectionBlock()),
        ('collections', CollectionSectionBlock()),
        ('observation', ObservationSectionBlock()),
        ('fabric', FabricSectionBlock()),
        ('philosophy', PhilosophySectionBlock()),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = 'Страница о бренде'


class CatalogPage(LatinSlugMixin, Page):
    intro_title = models.CharField(max_length=200, default="Коллекция", blank=True)
    intro_body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro_title'),
        FieldPanel('intro_body'),
    ]

    class Meta:
        verbose_name = 'Каталог'

    def get_context(self, request):
        context = super().get_context(request)
        context['products'] = ProductPage.objects.child_of(self).live().order_by(
            'color', 'print_type', '-first_published_at'
        )
        context['favorite_ids'] = get_favorite_ids(request)
        return context


class ProductGalleryImage(Orderable, models.Model):
    page = ParentalKey('ProductPage', on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ForeignKey(
        'wagtailimages.Image',
        on_delete=models.CASCADE,
        related_name='+',
        verbose_name="Фото",
    )

    panels = [FieldPanel('image')]


class ProductSizeStock(models.Model):
    SIZE_S = 'S'
    SIZE_M = 'M'
    SIZE_L = 'L'
    SIZE_XL = 'XL'
    SIZE_CHOICES = [
        (SIZE_S, 'S'),
        (SIZE_M, 'M'),
        (SIZE_L, 'L'),
        (SIZE_XL, 'XL'),
    ]

    page = ParentalKey('ProductPage', on_delete=models.CASCADE, related_name='size_stocks')
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    quantity = models.PositiveIntegerField(default=0, verbose_name="Остаток, шт.")

    panels = [FieldPanel('size'), FieldPanel('quantity')]


class ProductPage(LatinSlugMixin, Page):
    COLOR_MILK = 'milk'
    COLOR_OLIVE = 'olive'
    COLOR_ORANGE = 'orange'
    COLOR_TERRACOTTA = 'terracotta'
    COLOR_CHOICES = [
        (COLOR_MILK, 'Молочный'),
        (COLOR_OLIVE, 'Оливковый'),
        (COLOR_ORANGE, 'Оранжевый'),
        (COLOR_TERRACOTTA, 'Терракотовый'),
    ]

    PRINT_EMBROIDERY = 'embroidery'
    PRINT_PRINT = 'print'
    PRINT_TYPE_CHOICES = [
        (PRINT_EMBROIDERY, 'Вышивка'),
        (PRINT_PRINT, 'Печать'),
    ]

    collection_name = models.CharField(max_length=100, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default=COLOR_MILK, verbose_name="Цвет")
    print_type = models.CharField(max_length=20, choices=PRINT_TYPE_CHOICES, default=PRINT_PRINT, verbose_name="Тип принта")
    main_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Главное фото"
    )
    body = RichTextField(blank=True)
    price = models.CharField(max_length=50, blank=True)
    old_price = models.CharField(max_length=50, blank=True, verbose_name="Цена до скидки")
    fabric_info = models.TextField(blank=True, verbose_name="Состав")
    care_info = models.TextField(blank=True, verbose_name="Уход")
    fit_notes = models.TextField(
        blank=True,
        verbose_name="Посадка",
        help_text="По одному пункту на строку, например: «Свободная посадка», «Спущенное плечо». "
                  "Первая строка попадает в краткие характеристики. Пусто — блок «Как сидит» не показывается.",
    )
    model_size = models.CharField(
        max_length=4,
        blank=True,
        choices=[('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL')],
        verbose_name="Размер на модели",
    )
    model_height = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Рост модели, см",
    )

    AVAILABLE = 'available'
    COMING_SOON = 'coming_soon'
    SOLD_OUT = 'sold_out'
    STATUS_CHOICES = [
        (AVAILABLE, 'В наличии'),
        (COMING_SOON, 'Скоро'),
        (SOLD_OUT, 'Нет в наличии'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=AVAILABLE)

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('collection_name'),
            FieldPanel('short_description'),
            FieldPanel('color'),
            FieldPanel('print_type'),
            FieldPanel('price'),
            FieldPanel('old_price'),
            FieldPanel('status'),
        ], heading="Основное"),
        FieldPanel('main_image'),
        InlinePanel('gallery_images', max_num=5, label="Доп. фото (до 5, плюс главное = 6)"),
        InlinePanel('size_stocks', max_num=4, label="Остатки по размерам"),
        FieldPanel('body'),
        MultiFieldPanel([
            FieldPanel('fabric_info'),
            FieldPanel('care_info'),
        ], heading="О товаре"),
        MultiFieldPanel([
            FieldPanel('fit_notes'),
            FieldPanel('model_size'),
            FieldPanel('model_height'),
        ], heading="Посадка и модель (необязательно)"),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        context['is_favorite'] = self.id in get_favorite_ids(request)
        context['purchase_state'] = self.purchase_state(settings.SALES_MODE == 'preorder')
        context['section_images'] = self.section_images()
        context['related_products'] = self.related_products()
        context['size_chart'] = SIZE_CHART
        context['favorite_ids'] = get_favorite_ids(request)
        context['in_cart_sizes'] = get_product_cart_sizes(request, self.id)
        return context

    # --- Данные для страницы товара (всё из существующих полей) ---

    def purchase_state(self, is_preorder):
        """Одно согласованное состояние: preorder / available / coming_soon / sold_out."""
        if self.status == self.COMING_SOON:
            return 'coming_soon'
        stocks = self.sorted_size_stocks
        if self.status != self.AVAILABLE or (stocks and not any(s.quantity for s in stocks)):
            return 'sold_out'
        return 'preorder' if is_preorder else 'available'

    @property
    def composition(self):
        return parse_composition(self.fabric_info)

    @property
    def density(self):
        return parse_density(self.fabric_info)

    @property
    def fabric(self):
        return parse_fabric(self.fabric_info)

    @property
    def fit_lines(self):
        return split_lines(self.fit_notes)

    @property
    def quick_specs(self):
        """Строка под заголовком: состав · плотность · посадка · техника."""
        specs = [self.composition, self.density]
        if self.fit_lines:
            specs.append(self.fit_lines[0].lower())
        specs.append(self.get_print_type_display().lower())
        return [s for s in specs if s]

    @property
    def print_name(self):
        """Название принта так, как оно записано у товара: текст в «ёлочках» из заголовка."""
        match = re.search(r"«([^»]+)»", self.title)
        return match.group(1) if match else self.title

    # Персонаж принта для полупрозрачного слоя в «Истории принта»: только если он
    # действительно есть в названии товара; иначе — нейтральная хвойная ветка.
    STORY_MOTIFS = [('птиц', 'bird-branch'), ('ёж', 'hedgehog'), ('белк', 'squirrel')]

    @property
    def story_motif(self):
        name = self.print_name.lower()
        for keyword, motif in self.STORY_MOTIFS:
            if keyword in name:
                return motif
        return 'pine-branch'

    @property
    def material_word(self):
        """Основной материал из состава: «95% хлопок, 5% лайкра» → «хлопок»."""
        match = re.search(r"%\s*([а-яё]+)", self.composition, re.IGNORECASE)
        return match.group(1) if match else ""

    @property
    def about_note_lines(self):
        """Вертикальная подпись блока «О вещи»: цвет, материал, техника — только реальные значения."""
        lines = [self.get_color_display(), self.material_word, self.get_print_type_display()]
        return [line for line in lines if line]

    @property
    def tech_facts(self):
        """Крупные факты технической секции: (значение, подпись, это слово, а не число)."""
        facts = []
        density = re.match(r"(\d+)\s*(.+)", self.density)
        if density:
            facts.append((density.group(1), density.group(2), False))
        for part in self.composition.split(","):
            match = re.match(r"\s*(\d+\s*%)\s*(.+)", part)
            if match:
                facts.append((match.group(1).replace(" ", ""), match.group(2).strip(), False))
        if self.fit_lines:
            facts.append((self.fit_lines[0], "посадка", True))
        facts.append((self.get_print_type_display(), "техника нанесения", True))
        return facts

    @property
    def key_facts(self):
        """Крупные характеристики блока «О вещи»: (значение, подпись)."""
        facts = []
        if self.density:
            facts.append((self.density, "плотность трикотажа"))
        if self.composition:
            facts.append((self.composition, "состав"))
        if self.fit_lines:
            facts.append((self.fit_lines[0], "посадка"))
        facts.append((self.get_print_type_display(), "техника нанесения"))
        return facts[:4]

    @property
    def spec_rows(self):
        rows = [
            ("Материал", self.composition),
            ("Плотность", self.density),
            ("Полотно", self.fabric),
            ("Посадка", ", ".join(self.fit_lines)),
            ("Цвет", self.get_color_display()),
            ("Техника нанесения", self.get_print_type_display()),
            ("Коллекция", self.collection_name),
            ("Артикул", self.sku),
        ]
        return [(label, value) for label, value in rows if value]

    @property
    def about_paragraphs(self):
        return about_paragraphs(self.fabric_info)

    @property
    def care_items(self):
        return care_items(self.care_info)

    def section_images(self):
        """Фото для блоков ниже первого экрана — без повторов одного кадра между блоками."""
        images = self.all_images
        pool = images[1:]
        story = pool[2] if len(pool) > 2 else (pool[-1] if pool else None)
        rest = [img for img in pool if img is not story]
        detail = pool[1] if len(pool) > 1 and pool[1] is not story else (rest[0] if rest else None)
        fit = [img for img in images if img is not story and img is not detail][:3]
        return {'story': story, 'detail': detail, 'fit': fit}

    def related_products(self, limit=4):
        qs = ProductPage.objects.live().exclude(id=self.id)
        if self.collection_name:
            qs = qs.filter(collection_name=self.collection_name)
        products = list(qs.order_by('-first_published_at'))
        products.sort(key=lambda p: p.status != self.AVAILABLE)
        return products[:limit]

    @property
    def all_images(self):
        images = []
        if self.main_image:
            images.append(self.main_image)
        images += [g.image for g in self.gallery_images.all() if g.image]
        return images

    @property
    def sku(self):
        return f"MS-{self.id:05d}"

    @property
    def discount_percent(self):
        old = parse_price_to_int(self.old_price)
        new = parse_price_to_int(self.price)
        if not old or not new or old <= new:
            return None
        return round((old - new) / old * 100)

    SIZE_ORDER = ['S', 'M', 'L', 'XL']

    @property
    def sorted_size_stocks(self):
        stocks = list(self.size_stocks.all())
        stocks.sort(key=lambda s: self.SIZE_ORDER.index(s.size) if s.size in self.SIZE_ORDER else 99)
        return stocks

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class FormField(AbstractFormField):
    page = ParentalKey('ContactPage', on_delete=models.CASCADE, related_name='form_fields')


class ContactPage(LatinSlugMixin, AbstractEmailForm):
    intro_title = models.CharField(max_length=200, default="Связаться с нами")
    intro_body = RichTextField(blank=True)
    thank_you_title = models.CharField(max_length=200, default="Спасибо")
    thank_you_text = RichTextField(blank=True)

    content_panels = AbstractEmailForm.content_panels + [
        FormSubmissionsPanel(),
        MultiFieldPanel([
            FieldPanel('intro_title'),
            FieldPanel('intro_body'),
        ], heading="Введение"),
        InlinePanel('form_fields', label="Поля формы"),
        MultiFieldPanel([
            FieldPanel('thank_you_title'),
            FieldPanel('thank_you_text'),
            FieldPanel('from_address'),
            FieldPanel('to_address'),
            FieldPanel('subject'),
        ], heading="Настройки формы"),
    ]

    class Meta:
        verbose_name = 'Страница контактов'


class DeliveryPage(LatinSlugMixin, Page):
    headline = models.CharField(max_length=200, default="Доставка и возврат")
    intro = RichTextField(blank=True, verbose_name="Первый абзац")
    body = RichTextField(blank=True, verbose_name="Второй абзац")
    bottom_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Изображение внизу"
    )

    content_panels = Page.content_panels + [
        FieldPanel('headline'),
        FieldPanel('intro'),
        FieldPanel('body'),
        FieldPanel('bottom_image'),
    ]

    class Meta:
        verbose_name = 'Доставка и возврат'


class LegalPage(LatinSlugMixin, Page):
    body = RichTextField(verbose_name="Текст документа")

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = 'Юридическая страница'


@register_setting
class SiteSettings(BaseSiteSetting):
    delivery_info = RichTextField(blank=True, verbose_name="Доставка и возврат")
    payment_info = RichTextField(blank=True, verbose_name="Оплата")
    delivery_summary = models.TextField(
        blank=True,
        default="Доставка по России\nСДЭК · Яндекс Доставка · Почта России\nСтоимость рассчитывается при оформлении",
        verbose_name="Доставка — коротко (под кнопкой)",
        help_text="Первая строка — заголовок, остальные — пояснения. Пусто — строка не показывается.",
    )
    payment_summary = models.TextField(
        blank=True,
        default="Оплата\nБанковской картой на сайте",
        verbose_name="Оплата — коротко (под кнопкой)",
        help_text="Первая строка — заголовок, остальные — пояснения. Пусто — строка не показывается.",
    )

    product_page_blocks = StreamField(
        EDITORIAL_BLOCKS,
        use_json_field=True,
        blank=True,
        verbose_name="Блоки внизу страницы товара",
        help_text="Показываются на всех страницах товаров перед «Другими лесными жителями». "
                  "Те же блоки, что на главной: «По дороге», «Туда, где тише», тёмная сцена и другие.",
    )

    panels = [
        FieldPanel('delivery_info'),
        FieldPanel('payment_info'),
        FieldPanel('delivery_summary'),
        FieldPanel('payment_summary'),
        FieldPanel('product_page_blocks'),
    ]

    @property
    def delivery_summary_lines(self):
        return split_lines(self.delivery_summary)

    @property
    def payment_summary_lines(self):
        return split_lines(self.payment_summary)

    class Meta:
        verbose_name = 'Товары: доставка и оплата'


class Order(models.Model):
    STATUS_NEW = 'new'
    STATUS_PAID = 'paid'
    STATUS_SHIPPED = 'shipped'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_PAID, 'Оплачен'),
        (STATUS_SHIPPED, 'Отправлен'),
        (STATUS_COMPLETED, 'Завершён'),
        (STATUS_CANCELLED, 'Отменён'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="Покупатель",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, verbose_name="Статус")

    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    city = models.CharField(max_length=100, verbose_name="Город")
    street = models.CharField(max_length=255, verbose_name="Улица")
    house = models.CharField(max_length=50, verbose_name="Дом, квартира")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Индекс")
    comment = models.TextField(blank=True, verbose_name="Комментарий к заказу")

    total = models.PositiveIntegerField(default=0, verbose_name="Сумма заказа")
    payment_id = models.CharField(max_length=64, blank=True, verbose_name="ID платежа ЮKassa")
    payment_idempotence_key = models.CharField(max_length=64, blank=True, verbose_name="Idempotence-Key платежа")
    checkout_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        verbose_name="Ключ отправки формы",
        help_text="Уникален: повторный POST той же формы checkout не создаёт второй заказ.",
    )
    is_preorder = models.BooleanField(
        default=False,
        verbose_name="Предзаказ",
        help_text="Оформлен в режиме SALES_MODE=preorder — оплата через ЮKassa для него не запрашивалась.",
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ №{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Заказ")
    product = models.ForeignKey(
        'website.ProductPage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name="Товар",
    )
    product_title = models.CharField(max_length=255, verbose_name="Название товара")
    size = models.CharField(max_length=10, blank=True, verbose_name="Размер")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    unit_price = models.PositiveIntegerField(default=0, verbose_name="Цена за штуку")

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"

    def __str__(self):
        return f"{self.product_title} × {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
