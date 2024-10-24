from django import template

register = template.Library()

@register.filter
def format_points(value):
    try:
        formatted_value = f"{value:,}".replace(",", ".")
        return formatted_value
    except (ValueError, TypeError):
        return value

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)