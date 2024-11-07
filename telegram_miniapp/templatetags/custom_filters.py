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

@register.filter
def calculate_cost(booster, booster_quantities):
    quantity = booster_quantities.get(booster.id, 0)
    return int(float(booster.cost) + (float(booster.cost) * (0.02 * float(quantity))))