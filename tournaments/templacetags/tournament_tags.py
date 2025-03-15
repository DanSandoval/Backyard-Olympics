from django import template

register = template.Library()

@register.filter
def sum_wagers(wagers):
    """Calculate the sum of wager points"""
    return sum(wager.points for wager in wagers)