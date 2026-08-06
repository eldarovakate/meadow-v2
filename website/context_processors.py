from .cart import get_cart_count
from .favorites import get_favorite_count


def cart(request):
    return {'cart_item_count': get_cart_count(request)}


def favorites(request):
    return {'favorite_count': get_favorite_count(request)}
