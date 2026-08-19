from .utils import parse_price_to_int

SESSION_KEY = "cart"


def _make_key(product_id, size):
    return f"{product_id}:{size or '-'}"


def get_cart(request):
    return dict(request.session.get(SESSION_KEY, {}))


def _save_cart(request, cart):
    request.session[SESSION_KEY] = cart
    request.session.modified = True


def add_item(request, product_id, size, quantity=1, max_quantity=None):
    cart = get_cart(request)
    key = _make_key(product_id, size)
    current = cart.get(key, 0)
    new_quantity = current + quantity
    if max_quantity is not None:
        new_quantity = min(new_quantity, max_quantity)
    cart[key] = new_quantity
    _save_cart(request, cart)
    return new_quantity


def remove_item(request, product_id, size):
    cart = get_cart(request)
    cart.pop(_make_key(product_id, size), None)
    _save_cart(request, cart)


def update_quantity(request, product_id, size, quantity, max_quantity=None):
    cart = get_cart(request)
    key = _make_key(product_id, size)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        if max_quantity is not None:
            quantity = min(quantity, max_quantity)
        cart[key] = quantity
    _save_cart(request, cart)


def get_cart_count(request):
    return sum(get_cart(request).values())


def get_cart_lines(request):
    from .models import ProductPage

    cart = get_cart(request)
    if not cart:
        return []

    product_ids = {int(key.split(':', 1)[0]) for key in cart}
    products = {p.id: p for p in ProductPage.objects.filter(id__in=product_ids).live()}

    lines = []
    for key, quantity in cart.items():
        product_id_str, size = key.split(':', 1)
        product = products.get(int(product_id_str))
        if not product:
            continue
        size = None if size == '-' else size
        unit_price = parse_price_to_int(product.price) or 0
        lines.append({
            'product': product,
            'size': size,
            'quantity': quantity,
            'unit_price': unit_price,
            'subtotal': unit_price * quantity,
        })
    return lines


def get_cart_total(request):
    return sum(line['subtotal'] for line in get_cart_lines(request))


def clear_cart(request):
    _save_cart(request, {})
