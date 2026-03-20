from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.models import Image
from modelcluster.fields import ParentalKey
from wagtail.contrib.forms.models import AbstractFormField, AbstractEmailForm
from wagtail.contrib.forms.panels import FormSubmissionsPanel


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
    intro_title = models.CharField(max_length=200, default="Коллекция")
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
        return context


class ProductPage(Page):
    collection_name = models.CharField(max_length=100, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    body = RichTextField(blank=True)
    price = models.CharField(max_length=50, blank=True)
    fabric_info = models.TextField(blank=True, verbose_name="О ткани")
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
            FieldPanel('status'),
        ], heading="Основное"),
        FieldPanel('body'),
        MultiFieldPanel([
            FieldPanel('fabric_info'),
            FieldPanel('care_info'),
        ], heading="О товаре"),
    ]

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
