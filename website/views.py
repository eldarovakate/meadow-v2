from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import AddressForm, ProfileForm
from accounts.models import Profile

from .cart import add_item, get_cart_count, get_cart_lines, get_cart_total, remove_item, update_quantity
from .favorites import get_favorite_count, get_favorite_ids, toggle_favorite
from .models import ProductPage


def favorites_view(request):
    favorite_ids = get_favorite_ids(request)
    products = ProductPage.objects.filter(id__in=favorite_ids).live()
    return render(request, "website/favorites_page.html", {"products": products, "favorite_ids": favorite_ids})


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

    return render(request, "website/account_page.html", {
        "profile_form": profile_form,
        "address_form": address_form,
        "password_form": password_form,
    })


def cart_view(request):
    lines = get_cart_lines(request)
    total = get_cart_total(request)
    return render(request, "website/cart_page.html", {"lines": lines, "total": total})


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
