from django.urls import path

from . import views

urlpatterns = [
    path("favorites/", views.favorites_view, name="favorites"),
    path("favorites/toggle/<int:page_id>/", views.favorite_toggle_view, name="favorite_toggle"),
    path("account/", views.account_view, name="account"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:page_id>/", views.cart_add_view, name="cart_add"),
    path("cart/remove/<int:page_id>/<str:size>/", views.cart_remove_view, name="cart_remove"),
    path("cart/update/<int:page_id>/<str:size>/", views.cart_update_view, name="cart_update"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/success/<int:order_id>/", views.order_success_view, name="order_success"),
]
