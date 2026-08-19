from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "product_title", "size", "quantity", "unit_price"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "full_name", "phone", "status", "total"]
    list_filter = ["status", "created_at"]
    search_fields = ["full_name", "phone", "email"]
    readonly_fields = ["created_at", "user", "total"]
    inlines = [OrderItemInline]
