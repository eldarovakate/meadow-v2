from django.conf import settings

from .cart import get_cart_count
from .favorites import get_favorite_count
from .utils import format_date_ru, format_date_ru_short


def cart(request):
    return {'cart_item_count': get_cart_count(request)}


def favorites(request):
    return {'favorite_count': get_favorite_count(request)}


def sales_mode(request):
    return {
        'is_preorder': settings.SALES_MODE == 'preorder',
        'sales_open_date_ru': format_date_ru(settings.SALES_OPEN_DATE),
        'sales_open_date_short_ru': format_date_ru_short(settings.SALES_OPEN_DATE),
        'checkout_enabled': settings.CHECKOUT_ENABLED,
    }
