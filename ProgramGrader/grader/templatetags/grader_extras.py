from django import template

from ..scoring import fmt

register = template.Library()


@register.filter
def score(value):
    return fmt(value)


STATUS_LABELS = {'done': '已改', 'pending': '待改', 'review': '需複查', 'missing': '未交'}


@register.filter
def status_label(status):
    return STATUS_LABELS[status]
