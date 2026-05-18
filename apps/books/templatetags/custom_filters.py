from django import template

register = template.Library()


@register.filter
def splitlines(value):
    return value.splitlines()
