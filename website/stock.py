"""Атомарная резервация/освобождение остатков по размерам для payment/checkout flow."""

from django.db import transaction


class InsufficientStockError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def is_product_sellable(product):
    """Товар можно купить: опубликован, статус «В наличии» и есть цена."""
    from .models import ProductPage
    from .utils import parse_price_to_int

    return bool(
        product.live
        and product.status == ProductPage.AVAILABLE
        and parse_price_to_int(product.price)
    )


def reserve_stock_for_lines(lines):
    """
    Атомарно уменьшает остаток по размеру для каждой строки корзины (reservation).

    Это единственная серверная проверка перед созданием заказа (checkout и retry),
    поэтому она не доверяет содержимому корзины: товар должен продаваться,
    quantity >= 1, у товара с размерами размер обязателен и должен существовать
    в остатках, у товара без размеров размера быть не может.
    При любой ошибке — InsufficientStockError, ничего не меняется (rollback).
    """
    from .models import ProductSizeStock

    with transaction.atomic():
        for line in lines:
            product = line["product"]
            size = line.get("size")
            quantity = line["quantity"]

            if not is_product_sellable(product):
                raise InsufficientStockError(f"Товар «{product.title}» сейчас недоступен для заказа")
            if not isinstance(quantity, int) or quantity < 1:
                raise InsufficientStockError(f"Неверное количество товара «{product.title}»")

            has_sizes = ProductSizeStock.objects.filter(page_id=product.id).exists()
            if not has_sizes:
                if size:
                    raise InsufficientStockError(f"У товара «{product.title}» нет размера {size}")
                continue
            if not size:
                raise InsufficientStockError(f"Выберите размер товара «{product.title}»")

            stock = (
                ProductSizeStock.objects
                .select_for_update()
                .filter(page_id=product.id, size=size)
                .first()
            )
            if not stock:
                raise InsufficientStockError(f"У товара «{product.title}» нет размера {size}")
            if stock.quantity < quantity:
                raise InsufficientStockError(f"Размер {size} товара «{product.title}» закончился")
            stock.quantity -= quantity
            stock.save(update_fields=["quantity"])


def release_stock_for_order(order):
    """
    Возвращает остаток по всем позициям заказа (ровно один раз на вызов).
    Вызывающая сторона отвечает за идемпотентность — вызывать только под
    select_for_update()-локом заказа и только при реальном переходе статуса.
    """
    from .models import ProductSizeStock

    for item in order.items.all():
        if not item.size or not item.product_id:
            continue
        stock = (
            ProductSizeStock.objects
            .select_for_update()
            .filter(page_id=item.product_id, size=item.size)
            .first()
        )
        if stock:
            stock.quantity += item.quantity
            stock.save(update_fields=["quantity"])
