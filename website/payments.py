"""
Единая точка интеграции с ЮKassa.

Ключевое правило: локальный Order.status меняется ТОЛЬКО на основании ответа
Payment.find_one() из API ЮKassa — никогда напрямую по данным входящего webhook
JSON. И webhook, и return-страница вызывают одну и ту же sync_order_payment().
"""

import json
import logging
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


class PaymentAPIUnavailable(Exception):
    """API ЮKassa временно недоступно — статус заказа менять нельзя, нужен повтор."""


class WebhookMalformed(Exception):
    """Тело webhook-запроса не является валидным JSON."""


class YooKassaClient:
    """
    Единственная точка соприкосновения с пакетом `yookassa`.

    Реальный SDK импортируется лениво внутри методов, так что этот модуль
    (и всё, что его импортирует) остаётся рабочим, даже если `yookassa` не
    установлен. В тестах достаточно замокать сам объект `yookassa_client`
    (или его методы) — не нужно подменять пакет `yookassa` в sys.modules.
    """

    def _configure(self):
        from yookassa import Configuration

        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    def create_payment(self, payload, idempotence_key):
        from yookassa import Payment

        self._configure()
        return Payment.create(payload, idempotence_key)

    def find_payment(self, payment_id):
        from yookassa import Payment

        self._configure()
        return Payment.find_one(payment_id)


yookassa_client = YooKassaClient()


def _get_or_create_idempotence_key(order):
    """
    Стабильный Idempotence-Key на одну платёжную попытку.

    Генерируется один раз и сохраняется ДО сетевого вызова к ЮKassa, поэтому
    повтор той же попытки (например, после сетевого таймаута) переиспользует
    тот же ключ — ЮKassa вернёт исходный Payment вместо создания второго.
    Новая попытка (retry после подтверждённой отмены) явно очищает это поле
    перед вызовом create_order_payment, чтобы получить новый ключ.
    """
    if not order.payment_idempotence_key:
        order.payment_idempotence_key = uuid.uuid4().hex
        order.save(update_fields=["payment_idempotence_key"])
    return order.payment_idempotence_key


def create_order_payment(order, return_url):
    """Создаёт платёж в ЮKassa (или переиспользует ответ по тому же Idempotence-Key) и возвращает ссылку на оплату."""
    idempotence_key = _get_or_create_idempotence_key(order)
    payment = yookassa_client.create_payment(
        {
            "amount": {"value": f"{order.total:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": f"Заказ №{order.id} — Meadow Shore",
            "metadata": {"order_id": str(order.id)},
        },
        idempotence_key,
    )
    order.payment_id = payment.id
    order.save(update_fields=["payment_id"])
    return payment.confirmation.confirmation_url


def _fetch_verified_payment(payment_id):
    try:
        return yookassa_client.find_payment(payment_id)
    except Exception as exc:
        logger.error("ЮKassa: API недоступно при проверке платежа %s (%s)", payment_id, exc.__class__.__name__)
        raise PaymentAPIUnavailable(payment_id) from exc


def _payment_matches_order(payment, order):
    """Полная проверка ответа API против локального заказа — единственный источник истины."""
    if payment.id != order.payment_id:
        return False

    amount = getattr(payment, "amount", None)
    if amount is None:
        return False
    if getattr(amount, "currency", None) != "RUB":
        return False
    try:
        amount_value = Decimal(amount.value)
    except (InvalidOperation, TypeError, AttributeError):
        return False
    if amount_value != Decimal(order.total):
        return False

    metadata_order_id = (getattr(payment, "metadata", None) or {}).get("order_id")
    try:
        metadata_order_id = int(metadata_order_id)
    except (TypeError, ValueError):
        return False
    if metadata_order_id != order.id:
        return False

    return True


def mark_order_paid(order):
    """
    Идемпотентный переход NEW -> PAID.

    Уведомление планируется через transaction.on_commit() изнутри локи —
    оно физически не отправится, если внешняя транзакция (в т.ч. более
    широкая, если mark_order_paid() когда-нибудь вызовут из другого atomic())
    откатится, и не продублируется на повторном/параллельном webhook —
    on_commit регистрируется только на той ветке, где реально произошёл
    переход NEW -> PAID (см. guard по locked.status выше).
    """
    from .models import Order
    from .notifications import send_payment_confirmed_notification

    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status != Order.STATUS_NEW:
            return locked
        locked.status = Order.STATUS_PAID
        locked.save(update_fields=["status"])
        transaction.on_commit(lambda: send_payment_confirmed_notification(locked))

    return locked


def mark_order_cancelled(order):
    """Идемпотентный переход NEW -> CANCELLED. Возвращает stock ровно один раз."""
    from .models import Order
    from .stock import release_stock_for_order

    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status != Order.STATUS_NEW:
            return locked
        locked.status = Order.STATUS_CANCELLED
        locked.save(update_fields=["status"])
        release_stock_for_order(locked)

    return locked


def sync_order_payment(order, expected_payment_id=None):
    """
    Общий механизм синхронизации, используемый и webhook'ом, и return-страницей.

    payment_id из webhook JSON (или order.payment_id для return-страницы)
    используется только как указатель — реальные данные всегда берутся из
    Payment.find_one(). Если verified-платёж не совпадает с заказом
    (id/сумма/валюта/metadata.order_id) — заказ не меняется, пишется warning.

    Возвращает (order, payment). payment может быть None, если у заказа ещё
    нет payment_id. Бросает PaymentAPIUnavailable при сетевой/API-ошибке —
    заказ в этом случае гарантированно не меняется.
    """
    payment_id = expected_payment_id or order.payment_id
    if not payment_id:
        return order, None

    payment = _fetch_verified_payment(payment_id)

    if not _payment_matches_order(payment, order):
        logger.warning(
            "ЮKassa: платёж %s не прошёл верификацию для заказа №%s (id/сумма/валюта/order_id не совпали)",
            payment_id, order.id,
        )
        return order, payment

    if payment.status == "succeeded":
        order = mark_order_paid(order)
    elif payment.status == "canceled":
        order = mark_order_cancelled(order)

    return order, payment


def process_webhook_event(raw_body):
    """
    Обрабатывает сырое тело webhook ЮKassa.

    JSON парсится только чтобы достать event/payment id — дальше вся проверка
    идёт через API (см. sync_order_payment). Неизвестные/неинтересующие
    события и заказы, не найденные по payment_id, безопасно игнорируются
    (вызывающая сторона отвечает 200). PaymentAPIUnavailable пробрасывается
    наверх, чтобы webhook-view ответил кодом, побуждающим ЮKassa повторить
    доставку.
    """
    try:
        payload = json.loads(raw_body)
    except (ValueError, TypeError) as exc:
        raise WebhookMalformed() from exc

    if not isinstance(payload, dict):
        raise WebhookMalformed()

    event = payload.get("event")
    payment_id = (payload.get("object") or {}).get("id")

    if event not in ("payment.succeeded", "payment.canceled") or not payment_id:
        return

    from .models import Order

    order = Order.objects.filter(payment_id=payment_id).first()
    if not order:
        logger.warning("ЮKassa webhook: заказ с payment_id=%s не найден", payment_id)
        return

    sync_order_payment(order, expected_payment_id=payment_id)
