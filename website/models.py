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

from .favorites import get_favorite_ids
from .utils import parse_price_to_int


class AboutPage(Page):
    tagline = models.CharField(max_length=100, blank=True, default="О нас")
    hero_title = models.CharField(max_length=200, default="Тихая красота природы")
    hero_subtitle = RichTextField(blank=True)

    story_title = models.CharField(max_length=200, blank=True, default="История бренда")
    story_body = RichTextField(blank=True)

    values_title = models.CharField(max_length=200, blank=True, default="Наши ценности")
    value_one_title = models.CharField(max_length=100, blank=True)
    value_one_body = models.TextField(blank=True)
    value_two_title = models.CharField(max_length=100, blank=True)
    value_two_body = models.TextField(blank=True)
    value_three_title = models.CharField(max_length=100, blank=True)
    value_three_body = models.TextField(blank=True)
    value_four_title = models.CharField(max_length=100, blank=True)
    value_four_body = models.TextField(blank=True)

    closing_quote = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('tagline'),
            FieldPanel('hero_title'),
            FieldPanel('hero_subtitle'),
        ], heading="Hero"),
        MultiFieldPanel([
            FieldPanel('story_title'),
            FieldPanel('story_body'),
        ], heading="История"),
        MultiFieldPanel([
            FieldPanel('values_title'),
            FieldPanel('value_one_title'),
            FieldPanel('value_one_body'),
            FieldPanel('value_two_title'),
            FieldPanel('value_two_body'),
            FieldPanel('value_three_title'),
            FieldPanel('value_three_body'),
            FieldPanel('value_four_title'),
            FieldPanel('value_four_body'),
        ], heading="Ценности"),
        FieldPanel('closing_quote'),
    ]

    class Meta:
        verbose_name = 'Страница о бренде'


class CatalogPage(Page):
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
        context['products'] = ProductPage.objects.child_of(self).live().order_by('-first_published_at')
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


class ProductPage(Page):
    collection_name = models.CharField(max_length=100, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
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
            FieldPanel('price'),
            FieldPanel('old_price'),
            FieldPanel('status'),
        ], heading="Основное"),
        FieldPanel('main_image'),
        InlinePanel('gallery_images', max_num=4, label="Доп. фото (до 4, плюс главное = 5)"),
        InlinePanel('size_stocks', max_num=4, label="Остатки по размерам"),
        FieldPanel('body'),
        MultiFieldPanel([
            FieldPanel('fabric_info'),
            FieldPanel('care_info'),
        ], heading="О товаре"),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        context['is_favorite'] = self.id in get_favorite_ids(request)
        return context

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


class ContactPage(AbstractEmailForm):
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


class DeliveryPage(Page):
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


class LegalPage(Page):
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

    panels = [
        FieldPanel('delivery_info'),
        FieldPanel('payment_info'),
    ]

    class Meta:
        verbose_name = 'Товары: доставка и оплата'
