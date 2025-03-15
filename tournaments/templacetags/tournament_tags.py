from django import template

register = template.Library()

@register.filter
def sum_wagers(wagers):
    """Calculate the sum of wager points"""
    return sum(wager.points for wager in wagers)

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a variable key"""
    return dictionary.get(key)