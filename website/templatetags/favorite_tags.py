from django import template

register = template.Library()


@register.filter(name="in_list")
def in_list(value, the_list):
    return value in the_list
