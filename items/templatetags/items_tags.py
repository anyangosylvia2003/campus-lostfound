from django import template

register = template.Library()

@register.filter
def badge_class(value):
    classes = {
        'lost': 'badge-lost',
        'found': 'badge-found',
        'active': 'badge-active',
        'matched': 'bg-info text-dark',
        'claimed': 'badge-claimed',
        'resolved': 'badge-resolved',
        'donated': 'bg-secondary',
        'electronics': 'badge-electronics',
        'documents': 'badge-documents',
        'clothing': 'badge-clothing',
        'keys': 'bg-warning text-dark',
        'ids': 'bg-primary',
        'wallets': 'bg-success',
        'bags': 'bg-secondary',
        'others': 'badge-others',
    }
    return classes.get(value, 'bg-secondary')

@register.filter
def score_color(score):
    """Return Bootstrap color class based on match percentage."""
    try:
        s = int(score)
    except (TypeError, ValueError):
        return 'secondary'
    if s >= 70:
        return 'success'
    if s >= 40:
        return 'warning'
    return 'secondary'
