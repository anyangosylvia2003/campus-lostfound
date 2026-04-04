from django import template
from security.decorators import is_security

register = template.Library()

@register.filter(name='is_security_user')
def is_security_user(user):
    return is_security(user)
