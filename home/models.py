from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class CollectionCardBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=100, label="Название")
    subtitle = blocks.CharBlock(max_length=200, required=False, label="Подзаголовок")
    description = blocks.TextBlock(required=False, label="Описание")
    image = ImageChooserBlock(required=False, label="Изображение")
    link_text = blocks.CharBlock(max_length=50, default="Смотреть", label="Текст ссылки")

    class Meta:
        icon = 'image'
        label = 'Карточка коллекции'


class FeatureItemBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=100, label="Заголовок")
    description = blocks.TextBlock(label="Описание")

    class Meta:
        icon = 'tick'
        label = 'Преимущество'


class FeaturedProductBlock(blocks.StructBlock):
    name = blocks.CharBlock(max_length=100, label="Название")
    collection = blocks.CharBlock(max_length=100, required=False, label="Коллекция")
    price = blocks.CharBlock(max_length=50, required=False, label="Цена")
    image = ImageChooserBlock(required=False, label="Изображение")
    tag = blocks.CharBlock(max_length=50, required=False, label="Тег")

    class Meta:
        icon = 'tag'
        label = 'Товар'


class MarqueeItemBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=100, label="Текст")

    class Meta:
        icon = 'arrow-right'
        label = 'Элемент строки'


class HeroSectionBlock(blocks.StructBlock):
    headline = blocks.CharBlock(max_length=200, label="Главный заголовок")
    subheadline = blocks.CharBlock(max_length=300, required=False, label="Подзаголовок")
    cta_text = blocks.CharBlock(max_length=100, default="Смотреть коллекцию", label="Текст кнопки")
    cta_url = blocks.URLBlock(required=False, label="Ссылка кнопки")
    image = ImageChooserBlock(required=False, label="Фоновое изображение")

    class Meta:
        icon = 'pick'
        label = 'Hero секция'


class AboutSectionBlock(blocks.StructBlock):
    tagline = blocks.CharBlock(max_length=100, required=False, label="Тег")
    title = blocks.CharBlock(max_length=200, label="Заголовок")
    body = blocks.RichTextBlock(label="Текст")
    detail_one = blocks.CharBlock(max_length=100, required=False, label="Деталь 1")
    detail_two = blocks.CharBlock(max_length=100, required=False, label="Деталь 2")
    detail_three = blocks.CharBlock(max_length=100, required=False, label="Деталь 3")
    image = ImageChooserBlock(required=False, label="Изображение")

    class Meta:
        icon = 'doc-full'
        label = 'Блок о бренде'


class CollectionSectionBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200, label="Заголовок секции")
    cards = blocks.ListBlock(CollectionCardBlock(), label="Карточки")

    class Meta:
        icon = 'folder'
        label = 'Секция коллекций'


class MarqueeSectionBlock(blocks.StructBlock):
    items = blocks.ListBlock(MarqueeItemBlock(), label="Элементы строки")

    class Meta:
        icon = 'arrow-right'
        label = 'Бегущая строка'


class FeaturesSectionBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200, label="Заголовок секции")
    subtitle = blocks.CharBlock(max_length=300, required=False, label="Подзаголовок")
    items = blocks.ListBlock(FeatureItemBlock(), label="Преимущества")

    class Meta:
        icon = 'list-ul'
        label = 'Секция преимуществ'


class FabricSectionBlock(blocks.StructBlock):
    tagline = blocks.CharBlock(max_length=100, required=False, label="Тег")
    title = blocks.CharBlock(max_length=200, label="Заголовок")
    body = blocks.RichTextBlock(label="Текст")
    stat_one_value = blocks.CharBlock(max_length=50, required=False, label="Показатель 1: значение")
    stat_one_label = blocks.CharBlock(max_length=100, required=False, label="Показатель 1: подпись")
    stat_two_value = blocks.CharBlock(max_length=50, required=False, label="Показатель 2: значение")
    stat_two_label = blocks.CharBlock(max_length=100, required=False, label="Показатель 2: подпись")
    stat_three_value = blocks.CharBlock(max_length=50, required=False, label="Показатель 3: значение")
    stat_three_label = blocks.CharBlock(max_length=100, required=False, label="Показатель 3: подпись")
    image = ImageChooserBlock(required=False, label="Изображение")

    class Meta:
        icon = 'pick'
        label = 'Блок о ткани'


class FeaturedProductsSectionBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200, label="Заголовок секции")
    products = blocks.ListBlock(FeaturedProductBlock(), label="Товары")

    class Meta:
        icon = 'tag'
        label = 'Избранные товары'


class PhilosophySectionBlock(blocks.StructBlock):
    quote = blocks.TextBlock(label="Цитата / философия")
    attribution = blocks.CharBlock(max_length=100, required=False, label="Подпись")
    body = blocks.RichTextBlock(required=False, label="Текст")

    class Meta:
        icon = 'openquote'
        label = 'Блок философии'


class CTASectionBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200, label="Заголовок")
    subtitle = blocks.CharBlock(max_length=300, required=False, label="Подзаголовок")
    cta_text = blocks.CharBlock(max_length=100, label="Текст кнопки")
    cta_url = blocks.CharBlock(max_length=200, default="/collection/", label="Ссылка")

    class Meta:
        icon = 'mail'
        label = 'CTA блок'


class HomePage(Page):
    body = StreamField([
        ('hero', HeroSectionBlock()),
        ('about', AboutSectionBlock()),
        ('collections', CollectionSectionBlock()),
        ('marquee', MarqueeSectionBlock()),
        ('features', FeaturesSectionBlock()),
        ('fabric', FabricSectionBlock()),
        ('featured_products', FeaturedProductsSectionBlock()),
        ('philosophy', PhilosophySectionBlock()),
        ('cta', CTASectionBlock()),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = 'Главная страница'

    def get_context(self, request):
        context = super().get_context(request)
        return context
