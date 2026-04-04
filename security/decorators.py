from django.core.exceptions import PermissionDenied
from functools import wraps


def security_required(view_func):
    """Restrict a view to security staff only."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not is_security(request.user):
            raise PermissionDenied("Security staff access required.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def is_security(user):
    """Check if a user is active security staff."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'security_profile') and user.security_profile.is_active
