from django import template

from website.cart import format_rub

register = template.Library()


@register.filter(name="rub")
def rub(value):
    """4800 -> «4 800 ₽»."""
    try:
        return format_rub(value)
    except (TypeError, ValueError):
        return value
