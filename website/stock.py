"""Атомарная резервация/освобождение остатков по размерам для payment/checkout flow."""

from django.db import transaction


class InsufficientStockError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def reserve_stock_for_lines(lines):
    """
    Атомарно уменьшает остаток по размеру для каждой строки корзины (reservation).
    Строки без размера пропускаются — по ним остаток не ведётся.
    При нехватке хотя бы одной позиции — InsufficientStockError, ничего не меняется (rollback).
    """
    from .models import ProductSizeStock

    with transaction.atomic():
        for line in lines:
            size = line.get("size")
            if not size:
                continue
            stock = (
                ProductSizeStock.objects
                .select_for_update()
                .filter(page_id=line["product"].id, size=size)
                .first()
            )
            if not stock or stock.quantity < line["quantity"]:
                raise InsufficientStockError(
                    f"Размер {size} товара «{line['product'].title}» закончился"
                )
            stock.quantity -= line["quantity"]
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
