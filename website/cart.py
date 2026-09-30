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
    if key not in cart:
        # Только изменение существующей строки: новые позиции (в т.ч. «без размера»)
        # попадают в корзину исключительно через add_item с проверками в cart_add_view.
        return
    if quantity <= 0:
        cart.pop(key, None)
    else:
        if max_quantity is not None:
            quantity = min(quantity, max_quantity)
        cart[key] = quantity
    _save_cart(request, cart)


def get_product_cart_sizes(request, product_id):
    """Размеры этого товара, которые уже лежат в корзине ('-' — товар без размера)."""
    prefix = f"{product_id}:"
    return [key[len(prefix):] for key in get_cart(request) if key.startswith(prefix)]


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
        old_price = parse_price_to_int(product.old_price)
        old_unit_price = old_price if old_price and old_price > unit_price else None
        max_quantity = None
        size_stocks = list(product.size_stocks.all())
        if size_stocks:
            stock = next((s for s in size_stocks if s.size == size), None)
            max_quantity = stock.quantity if stock else 0
        lines.append({
            'key': key,
            'product': product,
            'size': size,
            'quantity': quantity,
            'unit_price': unit_price,
            'old_unit_price': old_unit_price,
            'subtotal': unit_price * quantity,
            'max_quantity': max_quantity,
        })
    return lines


def format_rub(amount):
    """4800 -> «4 800 ₽» (неразрывные пробелы)."""
    return f"{int(amount):,}".replace(",", " ") + " ₽"


def plural_items(count):
    """1 товар, 2 товара, 5 товаров."""
    if count % 10 == 1 and count % 100 != 11:
        word = "товар"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "товара"
    else:
        word = "товаров"
    return f"{count} {word}"


def get_cart_summary(lines):
    """Итог заказа: количество, сумма без скидки, скидка, итого."""
    count = sum(line['quantity'] for line in lines)
    total = sum(line['subtotal'] for line in lines)
    full_total = sum((line['old_unit_price'] or line['unit_price']) * line['quantity'] for line in lines)
    discount = full_total - total
    return {
        'count': count,
        'count_label': plural_items(count),
        'total': total,
        'total_display': format_rub(total),
        'full_total': full_total,
        'full_total_display': format_rub(full_total),
        'discount': discount,
        'discount_display': format_rub(discount),
    }


def line_payload(line):
    """Позиция корзины для JSON-ответов (мини-корзина, пересчёт на странице корзины)."""
    product = line['product']
    image = product.main_image or next(iter(product.all_images), None)
    return {
        'key': line['key'],
        'title': product.title,
        'url': product.url,
        'collection': product.collection_name,
        'technique': product.get_print_type_display(),
        'size': line['size'],
        'quantity': line['quantity'],
        'max_quantity': line['max_quantity'],
        'price_display': format_rub(line['unit_price']),
        'old_price_display': format_rub(line['old_unit_price']) if line['old_unit_price'] else '',
        'subtotal_display': format_rub(line['subtotal']),
        'image': image.get_rendition('fill-240x300').url if image else '',
    }


def find_line(lines, product_id, size):
    key = _make_key(product_id, size)
    return next((line for line in lines if line['key'] == key), None)


def get_cart_total(request):
    return sum(line['subtotal'] for line in get_cart_lines(request))


def clear_cart(request):
    _save_cart(request, {})
