from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='add_class')
def add_class(value, css_class):
    return value.as_widget(attrs={"class": css_class})

@register.filter(name='ltr')
def ltr(value):
    """
    Wraps the value in a span with LTR direction to fix RTL display issues
    for alphanumeric content like serial numbers and product codes.
    """
    if value:
        return mark_safe(f'<span class="ltr-content">{value}</span>')
    return value

@register.filter(name='ltr_code')
def ltr_code(value):
    """
    Wraps the value in a code tag with LTR direction to fix RTL display issues
    for alphanumeric content like serial numbers and product codes.
    """
    if value:
        return mark_safe(f'<code class="ltr-content">{value}</code>')
    return value 