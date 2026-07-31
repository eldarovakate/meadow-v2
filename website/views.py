from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .favorites import get_favorite_ids, toggle_favorite
from .models import ProductPage


def favorites_view(request):
    favorite_ids = get_favorite_ids(request)
    products = ProductPage.objects.filter(id__in=favorite_ids).live()
    return render(request, "website/favorites_page.html", {"products": products})


def account_view(request):
    return render(request, "website/account_page.html")


def cart_view(request):
    return render(request, "website/cart_page.html")


@require_POST
def favorite_toggle_view(request, page_id):
    get_object_or_404(ProductPage, id=page_id)
    is_favorite = toggle_favorite(request, page_id)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"is_favorite": is_favorite})

    next_url = request.POST.get("next") or "/"
    return redirect(next_url)
