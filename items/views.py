import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings
from django.http import HttpResponseForbidden

from .models import Item
from .forms import ItemForm, SearchForm, ContactOwnerForm
from security.decorators import is_security
from accounts.email_utils import send_campus_email
from accounts.models import EmailLog

logger = logging.getLogger(__name__)


def home(request):
    recent_lost  = Item.objects.filter(
        item_type=Item.TYPE_LOST, status=Item.STATUS_ACTIVE)[:6]
    recent_found = Item.objects.filter(
        item_type=Item.TYPE_FOUND, status=Item.STATUS_ACTIVE)[:6]
    stats = {
        'total':    Item.objects.count(),
        'lost':     Item.objects.filter(item_type=Item.TYPE_LOST,
                                        status=Item.STATUS_ACTIVE).count(),
        'found':    Item.objects.filter(item_type=Item.TYPE_FOUND,
                                        status=Item.STATUS_ACTIVE).count(),
        'resolved': Item.objects.filter(status=Item.STATUS_RESOLVED).count(),
    }
    return render(request, 'items/home.html', {
        'recent_lost':  recent_lost,
        'recent_found': recent_found,
        'stats':        stats,
    })


def item_list(request):
    form  = SearchForm(request.GET)
    items = Item.objects.select_related('owner').all()

    if form.is_valid():
        q        = form.cleaned_data.get('q')
        i_type   = form.cleaned_data.get('item_type')
        category = form.cleaned_data.get('category')
        color    = form.cleaned_data.get('color')
        location = form.cleaned_data.get('location')
        status   = form.cleaned_data.get('status')

        if q:
            items = items.filter(
                Q(title__icontains=q) | Q(description__icontains=q) |
                Q(brand__icontains=q) | Q(color__icontains=q)
            )
        if i_type:   items = items.filter(item_type=i_type)
        if category: items = items.filter(category=category)
        if color:    items = items.filter(color__icontains=color)
        if location: items = items.filter(location=location)
        if status:   items = items.filter(status=status)

    paginator = Paginator(items, settings.ITEMS_PER_PAGE)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'items/list.html', {
        'page_obj':    page_obj,
        'form':        form,
        'total_count': items.count(),
    })


def item_detail(request, pk):
    item          = get_object_or_404(Item.objects.select_related('owner'), pk=pk)
    scored_matches = item.get_matches(limit=5)
    contact_form  = ContactOwnerForm()
    return render(request, 'items/detail.html', {
        'item':           item,
        'scored_matches': scored_matches,
        'contact_form':   contact_form,
        'is_security_user': is_security(request.user),
    })


@login_required
def contact_owner(request, pk):
    item = get_object_or_404(Item.objects.select_related('owner'), pk=pk)

    if item.owner == request.user:
        messages.warning(request, 'You cannot contact yourself.')
        return redirect('items:detail', pk=pk)

    if request.method == 'POST':
        form = ContactOwnerForm(request.POST)
        if form.is_valid():
            sender_name  = request.user.get_full_name() or request.user.username
            sender_email = request.user.email
            subject_text = form.cleaned_data['subject']
            body         = form.cleaned_data['message']
            owner        = item.owner
            owner_name   = owner.get_full_name() or owner.username

            if not owner.email:
                messages.warning(
                    request,
                    f'{owner_name} has no email address on file. '
                    f'Please contact the Security Office for assistance.'
                )
                return redirect('items:detail', pk=pk)

            # Email to item owner
            sent = send_campus_email(
                subject=f'[Campus L&F] Someone is interested in your item — {item.title}',
                message=(
                    f'Hello {owner_name},\n\n'
                    f'{sender_name} has sent you a message regarding your '
                    f'{item.get_item_type_display().lower()} item "{item.title}".\n\n'
                    f'Subject: {subject_text}\n\n'
                    f'{body}\n\n'
                    f'─────────────────────────────\n'
                    f'To reply, log in to Campus Lost & Found and respond directly.\n'
                    f'Contact email: {sender_email}\n\n'
                    f'— Campus Lost & Found'
                ),
                recipient_email=owner.email,
                email_type=EmailLog.TYPE_CONTACT,
                recipient_user=owner,
            )

            if sent:
                # Confirmation to sender
                send_campus_email(
                    subject=f'[Campus L&F] Your message was sent — {item.title}',
                    message=(
                        f'Hello {sender_name},\n\n'
                        f'Your message to {owner_name} about "{item.title}" has been sent.\n\n'
                        f'They will reply to your email address: {sender_email}\n\n'
                        f'— Campus Lost & Found'
                    ),
                    recipient_email=sender_email,
                    email_type=EmailLog.TYPE_CONTACT,
                    recipient_user=request.user,
                )
                messages.success(
                    request,
                    f'✅ Your message has been sent to {owner_name}. '
                    f'They will reply to your email.'
                )
            else:
                messages.error(
                    request,
                    'Failed to send your message. Please try again or '
                    'contact the Security Office directly.'
                )

            return redirect('items:detail', pk=pk)

        else:
            scored_matches = item.get_matches(limit=5)
            return render(request, 'items/detail.html', {
                'item':             item,
                'scored_matches':   scored_matches,
                'contact_form':     form,
                'show_contact_modal': True,
                'is_security_user': is_security(request.user),
            })

    return redirect('items:detail', pk=pk)


@login_required
def item_create(request):
    initial = {}
    if request.GET.get('type') in [Item.TYPE_LOST, Item.TYPE_FOUND]:
        initial['item_type'] = request.GET.get('type')

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item       = form.save(commit=False)
            item.owner = request.user
            item.save()
            _run_auto_match(item)
            messages.success(
                request,
                f'Your {item.get_item_type_display().lower()} item '
                f'has been reported successfully!'
            )
            return redirect('items:detail', pk=item.pk)
    else:
        form = ItemForm(initial=initial)

    return render(request, 'items/form.html', {'form': form, 'action': 'Report Item'})


@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.owner != request.user:
        return HttpResponseForbidden('You can only edit your own items.')

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('items:detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)

    return render(request, 'items/form.html',
                  {'form': form, 'action': 'Edit Item', 'item': item})


@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.owner != request.user:
        return HttpResponseForbidden('You can only delete your own items.')

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully.')
        return redirect('items:list')

    return render(request, 'items/confirm_delete.html', {'item': item})


@login_required
def item_resolve(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.owner != request.user:
        return HttpResponseForbidden('You can only resolve your own items.')

    if request.method == 'POST':
        item.status = Item.STATUS_RESOLVED
        item.save()
        messages.success(request, 'Item marked as resolved. Glad it was recovered!')
        return redirect('items:detail', pk=item.pk)

    return render(request, 'items/confirm_resolve.html', {'item': item})


@login_required
def my_items(request):
    items = Item.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'items/my_items.html', {'items': items})


def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)


# ─── Auto-match engine ────────────────────────────────────────────────────────

def _run_auto_match(new_item):
    """On new item save, find 70%+ matches and email owners."""
    strong = new_item.get_strong_matches(threshold=70)
    if not strong:
        return

    if new_item.status == Item.STATUS_ACTIVE:
        new_item.status = Item.STATUS_MATCHED
        new_item.save(update_fields=['status'])

    for score, matched_item in strong:
        if matched_item.status == Item.STATUS_ACTIVE:
            matched_item.status = Item.STATUS_MATCHED
            matched_item.save(update_fields=['status'])
        _send_match_alert(new_item, matched_item, score)


def _send_match_alert(new_item, existing_item, score):
    """Email the owner of existing_item about a strong match."""
    owner = existing_item.owner
    if not owner.email:
        return

    owner_name = owner.get_full_name() or owner.username
    send_campus_email(
        subject=(
            f'[Campus L&F] 🎯 {score}% Match Found — '
            f'"{existing_item.title}"'
        ),
        message=(
            f'Hello {owner_name},\n\n'
            f'Good news! A newly posted item is a {score}% match for your '
            f'{existing_item.get_item_type_display().lower()} item '
            f'"{existing_item.title}".\n\n'
            f'── Possible Match ──────────────────\n'
            f'Title    : {new_item.title}\n'
            f'Category : {new_item.get_category_display()}\n'
            f'Location : {new_item.location}\n'
            f'Date     : {new_item.date}\n'
            f'Posted by: {new_item.owner.get_full_name() or new_item.owner.username}\n'
            f'────────────────────────────────────\n\n'
            f'Log in to Campus Lost & Found to view the match and '
            f'contact the reporter.\n\n'
            f'— Campus Lost & Found'
        ),
        recipient_email=owner.email,
        email_type=EmailLog.TYPE_MATCH_ALERT,
        recipient_user=owner,
    )
