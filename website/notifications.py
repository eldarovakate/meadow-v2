import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _build_order_summary(order):
    lines = [
        f"Новый заказ №{order.id}",
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
    summary = _build_order_summary(order)

    try:
        send_mail(
            subject=f"Новый заказ №{order.id} — Meadow Shore",
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
