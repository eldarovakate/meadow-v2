from django.urls import path

from . import views

urlpatterns = [
    path("favorites/", views.favorites_view, name="favorites"),
    path("favorites/toggle/<int:page_id>/", views.favorite_toggle_view, name="favorite_toggle"),
    path("account/", views.account_view, name="account"),
    path("cart/", views.cart_view, name="cart"),
]
