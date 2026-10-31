from django import template

from ..scoring import fmt

register = template.Library()


@register.filter
def score(value):
    return fmt(value)
