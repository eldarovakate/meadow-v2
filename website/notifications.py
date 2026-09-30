import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _build_order_summary(order, headline):
    lines = [
        headline,
        f"Сумма: {order.total} руб.",
        "",
        f"ФИО: {order.full_name}",
        f"Телефон: {order.phone}",
    ]
    if order.email:
        lines.append(f"Email: {order.email}")
    lines.append(f"Адрес: {order.city}, {order.street}, {order.house}" + (f", {order.postal_code}" if order.postal_code else ""))
    if order.comment:
        lines.append(f"Комментарий: {order.comment}")
    lines.append("")
    lines.append("Товары:")
    for item in order.items.all():
        size_part = f", размер {item.size}" if item.size else ""
        lines.append(f"— {item.product_title}{size_part} x {item.quantity} = {item.subtotal} руб.")
    return "\n".join(lines)


def send_order_notifications(order):
    """Первое уведомление: заказ создан, но НЕ оплачен (оплата подтверждается отдельным сообщением)."""
    if order.is_preorder:
        headline = f"Предзаказ №{order.id} создан, оплата не запрашивалась"
    else:
        headline = f"Заказ №{order.id} создан, ожидает оплаты"
    summary = _build_order_summary(order, headline)

    try:
        send_mail(
            subject=f"{headline} — Meadow Shore",
            message=summary,
            from_email=None,
            recipient_list=[settings.ORDER_NOTIFICATION_EMAIL],
        )
    except Exception:
        logger.exception("Не удалось отправить email-уведомление о заказе №%s", order.id)

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": summary},
                timeout=5,
                proxies={"http": None, "https": None},
            )
        except Exception:
            logger.exception("Не удалось отправить Telegram-уведомление о заказе №%s", order.id)


def send_payment_confirmed_notification(order):
    """Отправляется ровно один раз — вызывается только из идемпотентного перехода NEW -> PAID."""
    message = _build_order_summary(order, f"Оплата подтверждена: заказ №{order.id}")

    try:
        send_mail(
            subject=f"Заказ №{order.id} оплачен — Meadow Shore",
            message=message,
            from_email=None,
            recipient_list=[settings.ORDER_NOTIFICATION_EMAIL],
        )
    except Exception:
        logger.exception("Не удалось отправить email-уведомление об оплате заказа №%s", order.id)

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message},
                timeout=5,
                proxies={"http": None, "https": None},
            )
        except Exception:
            logger.exception("Не удалось отправить Telegram-уведомление об оплате заказа №%s", order.id)
