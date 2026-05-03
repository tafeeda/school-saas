from django import template

register = template.Library()

@register.filter
def dictget(dictionary, key):
    return dictionary.get(key)