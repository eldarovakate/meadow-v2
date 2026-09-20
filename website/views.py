import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.forms import AddressForm, ProfileForm
from accounts.models import Profile

from .cart import add_item, clear_cart, get_cart_count, get_cart_lines, get_cart_total, remove_item, update_quantity
from .favorites import get_favorite_count, get_favorite_ids, toggle_favorite
from .forms import CheckoutForm
from .models import Order, OrderItem, ProductPage
from .notifications import send_order_notifications
from .payments import (
    PaymentAPIUnavailable,
    WebhookMalformed,
    create_order_payment,
    mark_order_cancelled,
    process_webhook_event,
    sync_order_payment,
)
from .stock import InsufficientStockError, reserve_stock_for_lines

logger = logging.getLogger(__name__)


def favorites_view(request):
    favorite_ids = get_favorite_ids(request)
    products = ProductPage.objects.filter(id__in=favorite_ids).live()
    catalog_products = ProductPage.objects.live().exclude(id__in=favorite_ids).order_by('-first_published_at')
    return render(request, "website/favorites_page.html", {
        "products": products,
        "favorite_ids": favorite_ids,
        "catalog_products": catalog_products,
    })


def account_view(request):
    if not request.user.is_authenticated:
        return render(request, "website/account_page.html")

    profile, _ = Profile.objects.get_or_create(user=request.user)
    action = request.POST.get("action") if request.method == "POST" else None

    profile_form = ProfileForm(
        request.POST if action == "profile" else None,
        initial={
            "last_name": request.user.last_name,
            "first_name": request.user.first_name,
            "patronymic": profile.patronymic,
            "phone": profile.phone,
        },
    )
    address_form = AddressForm(
        request.POST if action == "address" else None,
        initial={
            "city": profile.city,
            "street": profile.street,
            "house": profile.house,
            "postal_code": profile.postal_code,
        },
    )
    password_form = PasswordChangeForm(
        request.user,
        request.POST if action == "password" else None,
    )

    if action == "profile" and profile_form.is_valid():
        request.user.last_name = profile_form.cleaned_data["last_name"]
        request.user.first_name = profile_form.cleaned_data["first_name"]
        request.user.save(update_fields=["last_name", "first_name"])
        profile.patronymic = profile_form.cleaned_data["patronymic"]
        profile.phone = profile_form.cleaned_data["phone"]
        profile.save(update_fields=["patronymic", "phone"])
        messages.success(request, "Личные данные обновлены.")
        return redirect("account")

    if action == "address" and address_form.is_valid():
        profile.city = address_form.cleaned_data["city"]
        profile.street = address_form.cleaned_data["street"]
        profile.house = address_form.cleaned_data["house"]
        profile.postal_code = address_form.cleaned_data.get("postal_code", "")
        profile.save(update_fields=["city", "street", "house", "postal_code"])
        messages.success(request, "Адрес сохранён.")
        return redirect("account")

    if action == "password" and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Пароль изменён.")
        return redirect("account")

    orders = request.user.orders.all().prefetch_related('items__product__main_image')

    return render(request, "website/account_page.html", {
        "profile_form": profile_form,
        "address_form": address_form,
        "password_form": password_form,
        "orders": orders,
    })


def cart_view(request):
    lines = get_cart_lines(request)
    total = get_cart_total(request)
    context = {"lines": lines, "total": total}
    if not lines:
        context["catalog_products"] = ProductPage.objects.live().order_by('-first_published_at')
        context["favorite_ids"] = get_favorite_ids(request)
    return render(request, "website/cart_page.html", context)


@login_required
def checkout_view(request):
    lines = get_cart_lines(request)
    if not lines:
        return redirect("cart")

    total = get_cart_total(request)
    profile = Profile.objects.filter(user=request.user).first()

    initial = {
        "full_name": f"{request.user.last_name} {request.user.first_name}".strip(),
        "email": request.user.email,
        "phone": profile.phone if profile else "",
        "city": profile.city if profile else "",
        "street": profile.street if profile else "",
        "house": profile.house if profile else "",
        "postal_code": profile.postal_code if profile else "",
    }

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Единственный источник истины для preorder/sales — server-side settings.SALES_MODE,
            # а не что-либо в request. Ниже это единственная развилка, решающая, вызывать ли ЮKassa.
            is_preorder = settings.SALES_MODE == "preorder"

            try:
                with transaction.atomic():
                    reserve_stock_for_lines(lines)
                    order = Order.objects.create(
                        user=request.user,
                        total=total,
                        is_preorder=is_preorder,
                        **form.cleaned_data,
                    )
                    for line in lines:
                        OrderItem.objects.create(
                            order=order,
                            product=line["product"],
                            product_title=line["product"].title,
                            size=line["size"] or "",
                            quantity=line["quantity"],
                            unit_price=line["unit_price"],
                        )
            except InsufficientStockError as exc:
                messages.error(request, str(exc))
                return render(request, "website/checkout_page.html", {"form": form, "lines": lines, "total": total})

            clear_cart(request)
            send_order_notifications(order)

            if is_preorder:
                # preorder = no payment: create_order_payment() (единственное место,
                # откуда вызывается ЮKassa для нового заказа) здесь не вызывается вовсе.
                return redirect("order_success", order_id=order.id)

            return_url = request.build_absolute_uri(reverse("order_success", args=[order.id]))
            try:
                payment_url = create_order_payment(order, return_url)
            except Exception:
                logger.exception("Не удалось создать платёж ЮKassa для заказа №%s", order.id)
                mark_order_cancelled(order)
                return redirect("order_success", order_id=order.id)

            return redirect(payment_url)
    else:
        form = CheckoutForm(initial=initial)

    return render(request, "website/checkout_page.html", {"form": form, "lines": lines, "total": total})


@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_preorder:
        return render(request, "website/order_success_page.html", {
            "order": order,
            "payment_state": "preorder",
        })

    payment_state = None
    if order.status == Order.STATUS_NEW and order.payment_id:
        try:
            order, _payment = sync_order_payment(order)
        except PaymentAPIUnavailable:
            payment_state = "unavailable"

    if payment_state is None:
        if order.status == Order.STATUS_PAID:
            payment_state = "paid"
        elif order.status == Order.STATUS_CANCELLED:
            payment_state = "cancelled" if order.payment_id else "create_failed"
        else:
            payment_state = "pending"

    return render(request, "website/order_success_page.html", {
        "order": order,
        "payment_state": payment_state,
    })


@login_required
@require_POST
def order_payment_retry_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_preorder:
        # Защита в глубину: даже прямой POST на этот эндпоинт не должен запускать
        # ЮKassa для предзаказа — тот же принцип, что и в checkout_view.
        messages.error(request, "Предзаказ не требует оплаты.")
        return redirect("order_success", order_id=order.id)

    if order.status == Order.STATUS_NEW and order.payment_id:
        try:
            order, _payment = sync_order_payment(order)
        except PaymentAPIUnavailable:
            messages.error(request, "Не удалось проверить оплату, попробуйте позже.")
            return redirect("order_success", order_id=order.id)

    if order.status != Order.STATUS_CANCELLED:
        messages.error(request, "Этот заказ нельзя повторно оплатить.")
        return redirect("order_success", order_id=order.id)

    lines = [
        {"product": item.product, "size": item.size, "quantity": item.quantity}
        for item in order.items.all()
        if item.product_id
    ]

    try:
        with transaction.atomic():
            reserve_stock_for_lines(lines)
            # order.payment_id set = предыдущий Payment был реально создан и затем
            # достоверно подтверждён как canceled через sync_order_payment() выше —
            # это новая, независимая попытка оплаты, ей нужен новый Idempotence-Key.
            # order.payment_id пустой = create_order_payment() тогда упал с
            # исключением ДО получения payment.id (см. checkout_view/этот же view
            # чуть ниже) — итог того вызова на стороне ЮKassa неизвестен, поэтому
            # сохранённый payment_idempotence_key НЕ сбрасываем: если тот запрос
            # всё же дошёл до ЮKassa, повтор с тем же ключом вернёт тот же Payment
            # вместо создания дубликата.
            if order.payment_id:
                order.payment_idempotence_key = ""
            order.status = Order.STATUS_NEW
            order.payment_id = ""
            order.save(update_fields=["status", "payment_id", "payment_idempotence_key"])
    except InsufficientStockError as exc:
        messages.error(request, str(exc))
        return redirect("order_success", order_id=order.id)

    return_url = request.build_absolute_uri(reverse("order_success", args=[order.id]))
    try:
        payment_url = create_order_payment(order, return_url)
    except Exception:
        logger.exception("Не удалось создать повторный платёж ЮKassa для заказа №%s", order.id)
        mark_order_cancelled(order)
        return redirect("order_success", order_id=order.id)

    return redirect(payment_url)


@csrf_exempt
@require_POST
def yookassa_webhook_view(request):
    try:
        process_webhook_event(request.body)
    except WebhookMalformed:
        return HttpResponseBadRequest()
    except PaymentAPIUnavailable:
        logger.error("ЮKassa webhook: API временно недоступно, запрошен повтор доставки")
        return HttpResponse(status=502)
    except Exception:
        logger.exception("Ошибка обработки webhook ЮKassa")
        return HttpResponseBadRequest()
    return HttpResponse(status=200)


@require_POST
def cart_add_view(request, page_id):
    product = get_object_or_404(ProductPage, id=page_id)
    size = request.POST.get("size") or None
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    size_stocks = list(product.size_stocks.all())
    max_quantity = None
    if size_stocks:
        stock = next((s for s in size_stocks if s.size == size), None)
        max_quantity = stock.quantity if stock else 0
        if not size or not max_quantity:
            if is_ajax:
                return JsonResponse({"ok": False, "error": "Выберите доступный размер"}, status=400)
            return redirect(request.POST.get("next") or product.url)

    add_item(request, product.id, size, quantity=1, max_quantity=max_quantity)
    cart_count = get_cart_count(request)

    if is_ajax:
        return JsonResponse({"ok": True, "cart_count": cart_count})

    next_url = request.POST.get("next") or "/cart/"
    return redirect(next_url)


@require_POST
def cart_remove_view(request, page_id, size):
    remove_item(request, page_id, None if size == "-" else size)
    return redirect(request.POST.get("next") or "cart")


@require_POST
def cart_update_view(request, page_id, size):
    size_value = None if size == "-" else size
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1

    max_quantity = None
    product = ProductPage.objects.filter(id=page_id).first()
    if product and size_value:
        stock = product.size_stocks.filter(size=size_value).first()
        max_quantity = stock.quantity if stock else 0

    update_quantity(request, page_id, size_value, quantity, max_quantity=max_quantity)
    return redirect("cart")


@require_POST
def favorite_toggle_view(request, page_id):
    get_object_or_404(ProductPage, id=page_id)
    is_favorite = toggle_favorite(request, page_id)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"is_favorite": is_favorite, "favorite_count": get_favorite_count(request)})

    next_url = request.POST.get("next") or "/"
    return redirect(next_url)


def design_lab_home_blocks_view(request):
    """Internal, non-CMS showcase of 10 alternative homepage image-section
    layouts. Not linked from navigation, not a Wagtail page — pure dev route
    for comparing composition ideas before any of them are considered for
    the real homepage."""
    from wagtail.images.models import Image as WagtailImage

    def img(title):
        return WagtailImage.objects.filter(title=title).first()

    context = {
        "hero_image": img("PsuGkckF-ND-VxnaQdfUhUR35BIpCEETnXUuhR163Qdl0qhOz8oba4GxStPptuksTIQPFciaSKiEzRfIdUlV6Gj2"),
        "sunset_image": img("Закат в лесу, макро"),
        "fabric_detail_image": img("DSC06505"),
        "hanging_shirt_image": img("DSC06487"),
        "bird_embroidery_image": img("DSC06385"),
        "bird_on_garment_image": img("Певчая птица_вышивка_молочная_дома"),
        "bird_embroidery_flat_image": img("Вышивка. 04. Птица певчая_Вышивка_2.jpg"),
        "model_field_image": img("DSC09128.jpg"),
        "model_back_squirrel_image": img("DSC09147.jpg"),
        "model_back_squirrel_close_image": img("DSC09171.jpg"),
        "model_bird_portrait_image": img("DSC09196.jpg"),
    }
    return render(request, "website/design_lab_home_blocks.html", context)
