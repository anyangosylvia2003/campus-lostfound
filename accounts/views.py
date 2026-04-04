import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q

from .forms import RegisterForm, ProfileForm
from .models import EmailLog
from .email_utils import send_campus_email

logger = logging.getLogger(__name__)


# ─── Registration ─────────────────────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('items:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Welcome email
            _send_welcome(user)
            messages.success(
                request,
                f'Welcome, {user.first_name or user.username}! '
                f'Your account has been created.'
            )
            return redirect('items:home')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


# ─── Email Log Dashboard (superuser only) ─────────────────────────────────────

@login_required
def email_log_dashboard(request):
    if not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    logs = EmailLog.objects.select_related('recipient_user').all()

    filter_type   = request.GET.get('type', '')
    filter_status = request.GET.get('status', '')
    search        = request.GET.get('q', '')

    if filter_type:   logs = logs.filter(email_type=filter_type)
    if filter_status: logs = logs.filter(status=filter_status)
    if search:        logs = logs.filter(recipient__icontains=search)

    stats = EmailLog.objects.aggregate(
        total=Count('id'),
        sent=Count('id',   filter=Q(status='sent')),
        failed=Count('id', filter=Q(status='failed')),
    )

    paginator = Paginator(logs, 30)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/email_log_dashboard.html', {
        'page_obj':          page_obj,
        'stats':             stats,
        'filter_type':       filter_type,
        'filter_status':     filter_status,
        'search':            search,
        'email_type_choices': EmailLog.TYPE_CHOICES,
        'status_choices':    EmailLog.STATUS_CHOICES,
    })


# ─── Internal email helpers ───────────────────────────────────────────────────

def _send_welcome(user):
    name = user.get_full_name() or user.username
    send_campus_email(
        subject='Welcome to Campus Lost & Found',
        message=(
            f"Hi {name},\n\n"
            f"Welcome to Campus Lost & Found! Your account has been created.\n\n"
            f"You can now:\n"
            f"  • Report lost or found items\n"
            f"  • Search for your belongings\n"
            f"  • Contact item reporters\n\n"
            f"Log in at any time to manage your items.\n\n"
            f"— Campus Lost & Found"
        ),
        recipient_email=user.email,
        email_type=EmailLog.TYPE_WELCOME,
        recipient_user=user,
    )
