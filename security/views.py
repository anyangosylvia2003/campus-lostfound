import io
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

from items.models import Item
from .models import (CustodyRecord, ClaimRequest, HandoverLog,
                     IncidentLog, SecurityProfile, CustodyTransferLog)
from .forms import (CustodyReceiveForm, ClaimRequestForm, ClaimReviewForm,
                    HandoverForm, IncidentLogForm, ItemStatusUpdateForm,
                    CustodyTransferForm, PromoteToSecurityForm)
from .decorators import security_required, is_security
from accounts.email_utils import send_campus_email
from accounts.models import EmailLog

logger = logging.getLogger(__name__)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@security_required
def dashboard(request):
    pending_claims  = ClaimRequest.objects.filter(
        status=ClaimRequest.STATUS_PENDING).select_related('item', 'claimant')
    in_custody      = CustodyRecord.objects.filter(
        custody_status=CustodyRecord.STATUS_IN_CUSTODY
    ).select_related('item', 'received_by')
    recent_handovers = HandoverLog.objects.select_related(
        'item', 'handed_to', 'handed_over_by')[:10]
    recent_incidents = IncidentLog.objects.select_related(
        'reported_by', 'subject_user')[:5]

    overdue_custody = [c for c in in_custody if c.is_overdue]

    stats = {
        'pending_claims':    pending_claims.count(),
        'in_custody':        in_custody.count(),
        'overdue_items':     len(overdue_custody),
        'total_items':       Item.objects.count(),
        'resolved_this_month': Item.objects.filter(
            status=Item.STATUS_RESOLVED,
            updated_at__month=timezone.now().month).count(),
        'total_handovers':   HandoverLog.objects.count(),
        'open_incidents':    IncidentLog.objects.filter(action_taken='').count(),
        'matched_items':     Item.objects.filter(
            status=Item.STATUS_MATCHED).count(),
    }
    hotspots = (Item.objects.values('location')
                .annotate(count=Count('id'))
                .order_by('-count')[:5])

    return render(request, 'security/dashboard.html', {
        'pending_claims':  pending_claims,
        'in_custody':      in_custody,
        'overdue_custody': overdue_custody,
        'recent_handovers': recent_handovers,
        'recent_incidents': recent_incidents,
        'stats':           stats,
        'hotspots':        hotspots,
    })


# ─── Analytics ────────────────────────────────────────────────────────────────

@security_required
def analytics(request):
    by_location = (Item.objects.values('location')
                   .annotate(total=Count('id'),
                             lost=Count('id', filter=Q(item_type='lost')),
                             found=Count('id', filter=Q(item_type='found')))
                   .order_by('-total')[:15])
    by_category = (Item.objects.values('category')
                   .annotate(total=Count('id')).order_by('-total'))
    by_status   = (Item.objects.values('status')
                   .annotate(total=Count('id')).order_by('-total'))

    from datetime import date
    try:
        from dateutil.relativedelta import relativedelta
        months = [date.today() - relativedelta(months=i) for i in range(5, -1, -1)]
    except ImportError:
        import calendar
        today = date.today()
        months = []
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            months.append(date(y, m, 1))

    monthly = []
    for d in months:
        monthly.append({
            'month':    d.strftime('%b %Y'),
            'resolved': Item.objects.filter(status=Item.STATUS_RESOLVED,
                                            updated_at__year=d.year,
                                            updated_at__month=d.month).count(),
            'reported': Item.objects.filter(created_at__year=d.year,
                                            created_at__month=d.month).count(),
        })

    total    = Item.objects.count()
    resolved = Item.objects.filter(status=Item.STATUS_RESOLVED).count()

    return render(request, 'security/analytics.html', {
        'by_location':   by_location,
        'by_category':   list(by_category),
        'by_status':     list(by_status),
        'monthly':       monthly,
        'resolution_rate': round((resolved / total * 100) if total else 0, 1),
        'total':         total,
        'resolved_total': resolved,
    })


# ─── Custody ──────────────────────────────────────────────────────────────────

@security_required
def receive_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if hasattr(item, 'custody'):
        messages.warning(request, 'This item is already logged in custody.')
        return redirect('security:custody_detail', pk=item.custody.pk)

    if request.method == 'POST':
        form = CustodyReceiveForm(request.POST)
        if form.is_valid():
            custody             = form.save(commit=False)
            custody.item        = item
            custody.received_by = request.user
            custody.save()
            item.status = Item.STATUS_ACTIVE
            item.save()
            messages.success(
                request,
                f'"{item.title}" logged into custody at {custody.storage_location}.'
            )
            return redirect('security:custody_detail', pk=custody.pk)
    else:
        form = CustodyReceiveForm()
    return render(request, 'security/receive_item.html', {'form': form, 'item': item})


@security_required
def custody_detail(request, pk):
    custody   = get_object_or_404(
        CustodyRecord.objects.select_related('item', 'received_by'), pk=pk)
    claims    = ClaimRequest.objects.filter(
        item=custody.item).select_related('claimant', 'reviewed_by')
    transfers = custody.transfers.select_related('transferred_by').all()
    return render(request, 'security/custody_detail.html', {
        'custody': custody, 'claims': claims, 'transfers': transfers,
    })


@security_required
def custody_list(request):
    records = CustodyRecord.objects.select_related('item', 'received_by').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        records = records.filter(custody_status=status_filter)
    overdue_ids = {c.pk for c in records if c.is_overdue}
    paginator   = Paginator(records, 20)
    page_obj    = paginator.get_page(request.GET.get('page'))
    return render(request, 'security/custody_list.html', {
        'page_obj':        page_obj,
        'status_filter':   status_filter,
        'custody_statuses': CustodyRecord.STATUS_CHOICES,
        'overdue_ids':     overdue_ids,
    })


@security_required
def transfer_custody(request, pk):
    custody = get_object_or_404(CustodyRecord, pk=pk)
    if request.method == 'POST':
        form = CustodyTransferForm(request.POST)
        if form.is_valid():
            transfer                 = form.save(commit=False)
            transfer.custody         = custody
            transfer.transferred_by  = request.user
            transfer.from_location   = custody.storage_location
            transfer.save()
            custody.storage_location = transfer.to_location
            custody.save(update_fields=['storage_location'])
            messages.success(request, f'Item moved to "{transfer.to_location}".')
            return redirect('security:custody_detail', pk=custody.pk)
    else:
        form = CustodyTransferForm(
            initial={'from_location': custody.storage_location})
    return render(request, 'security/transfer_custody.html',
                  {'form': form, 'custody': custody})


# ─── Claims ───────────────────────────────────────────────────────────────────

@login_required
def submit_claim(request, pk):
    item = get_object_or_404(Item, pk=pk)

    if item.item_type != Item.TYPE_FOUND:
        messages.error(request, 'You can only claim found items.')
        return redirect('items:detail', pk=pk)
    if not hasattr(item, 'custody'):
        messages.error(
            request,
            'This item has not been logged into security custody yet. '
            'Please contact the Security Office directly.'
        )
        return redirect('items:detail', pk=pk)
    if item.custody.custody_status != CustodyRecord.STATUS_IN_CUSTODY:
        messages.error(request, 'This item is not available for claiming at this time.')
        return redirect('items:detail', pk=pk)

    existing = ClaimRequest.objects.filter(item=item, claimant=request.user).first()
    if existing:
        messages.info(
            request,
            f'You already submitted a claim. Status: {existing.get_status_display()}'
        )
        return redirect('items:detail', pk=pk)

    if item.owner == request.user:
        messages.warning(request, 'You reported this item — you cannot claim it.')
        return redirect('items:detail', pk=pk)

    if request.method == 'POST':
        form = ClaimRequestForm(request.POST)
        if form.is_valid():
            claim          = form.save(commit=False)
            claim.item     = item
            claim.claimant = request.user
            claim.save()
            item.status    = Item.STATUS_CLAIMED
            item.save()
            _notify_security_new_claim(claim, request)
            messages.success(
                request,
                'Your claim has been submitted. '
                'Security will review it and contact you by email.'
            )
            return redirect('items:detail', pk=pk)
    else:
        form = ClaimRequestForm()

    return render(request, 'security/submit_claim.html', {'form': form, 'item': item})


@security_required
def review_claim(request, pk):
    claim = get_object_or_404(
        ClaimRequest.objects.select_related('item', 'claimant', 'item__custody'),
        pk=pk
    )
    if claim.status != ClaimRequest.STATUS_PENDING:
        messages.warning(request, 'This claim has already been reviewed.')
        return redirect('security:claim_detail', pk=pk)

    if request.method == 'POST':
        form = ClaimReviewForm(request.POST)
        if form.is_valid():
            decision             = form.cleaned_data['decision']
            claim.reviewed_by   = request.user
            claim.reviewed_at   = timezone.now()
            claim.security_notes = form.cleaned_data.get('security_notes', '')
            claimant_name        = (claim.claimant.get_full_name()
                                    or claim.claimant.username)

            if decision == 'approve':
                claim.status = ClaimRequest.STATUS_APPROVED
                claim.save()
                if hasattr(claim.item, 'custody'):
                    claim.item.custody.custody_status = CustodyRecord.STATUS_CLAIMED
                    claim.item.custody.save()
                sent = _notify_claimant_approved(claim, request)
                if sent:
                    messages.success(
                        request,
                        f'Claim approved. {claimant_name} has been notified by email.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Claim approved, but {claimant_name} has no email '
                        f'on file — notify them in person.'
                    )
                return redirect('security:process_handover', pk=claim.pk)
            else:
                claim.status           = ClaimRequest.STATUS_REJECTED
                claim.rejection_reason = form.cleaned_data['rejection_reason']
                claim.save()
                claim.item.status = Item.STATUS_ACTIVE
                claim.item.save()
                sent = _notify_claimant_rejected(claim)
                if sent:
                    messages.warning(
                        request,
                        f'Claim rejected. {claimant_name} has been notified by email.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Claim rejected, but {claimant_name} has no email '
                        f'on file — notify them in person.'
                    )
                return redirect('security:claim_detail', pk=pk)
    else:
        form = ClaimReviewForm()

    return render(request, 'security/review_claim.html',
                  {'form': form, 'claim': claim})


@security_required
def claim_detail(request, pk):
    claim   = get_object_or_404(
        ClaimRequest.objects.select_related(
            'item', 'claimant', 'reviewed_by', 'item__custody'),
        pk=pk
    )
    handover = getattr(claim, 'handover', None)
    return render(request, 'security/claim_detail.html',
                  {'claim': claim, 'handover': handover})


@security_required
def all_claims(request):
    claims        = ClaimRequest.objects.select_related(
        'item', 'claimant', 'reviewed_by').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        claims = claims.filter(status=status_filter)
    paginator = Paginator(claims, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'security/all_claims.html', {
        'page_obj':      page_obj,
        'status_filter': status_filter,
        'claim_statuses': ClaimRequest.STATUS_CHOICES,
    })


# ─── Handover ─────────────────────────────────────────────────────────────────

@security_required
def process_handover(request, pk):
    claim = get_object_or_404(
        ClaimRequest.objects.select_related('item', 'claimant', 'item__custody'),
        pk=pk
    )
    if claim.status != ClaimRequest.STATUS_APPROVED:
        messages.error(request, 'Handover can only be processed for approved claims.')
        return redirect('security:claim_detail', pk=pk)
    if hasattr(claim, 'handover'):
        messages.info(request, 'Handover already recorded.')
        return redirect('security:claim_detail', pk=pk)

    qr_verified = False
    if request.method == 'POST':
        submitted_token = request.POST.get('qr_token', '').strip()
        if submitted_token:
            if (str(claim.handover_token) == submitted_token
                    and not claim.handover_token_used):
                qr_verified = True
            else:
                messages.error(request, 'Invalid or already-used QR token.')
                return redirect('security:process_handover', pk=pk)

        form = HandoverForm(request.POST)
        if form.is_valid():
            handover                 = form.save(commit=False)
            handover.claim           = claim
            handover.item            = claim.item
            handover.handed_to       = claim.claimant
            handover.handed_over_by  = request.user
            handover.qr_verified     = qr_verified
            handover.save()

            claim.handover_token_used = True
            claim.save(update_fields=['handover_token_used'])

            claim.item.status = Item.STATUS_RESOLVED
            claim.item.save()
            if hasattr(claim.item, 'custody'):
                claim.item.custody.custody_status = CustodyRecord.STATUS_RETURNED
                claim.item.custody.save()

            _notify_handover_complete(handover)
            qr_note = ' (QR verified ✓)' if qr_verified else ''
            messages.success(
                request,
                f'Handover logged{qr_note}. '
                f'"{claim.item.title}" returned to {handover.collector_name}.'
            )
            return redirect('security:claim_detail', pk=claim.pk)
    else:
        form = HandoverForm(
            initial={'collector_name':
                     claim.claimant.get_full_name() or claim.claimant.username})

    qr_svg = _generate_qr_svg(str(claim.handover_token))
    return render(request, 'security/process_handover.html', {
        'form':          form,
        'claim':         claim,
        'qr_svg':        qr_svg,
        'handover_token': str(claim.handover_token),
        'token_used':    claim.handover_token_used,
    })


@login_required
def my_handover_qr(request, token):
    claim = get_object_or_404(ClaimRequest, handover_token=token)
    if claim.claimant != request.user:
        messages.error(request, 'This QR code is not yours.')
        return redirect('items:home')
    if claim.handover_token_used:
        messages.warning(request, 'This QR code has already been used.')
    qr_svg = _generate_qr_svg(str(claim.handover_token))
    return render(request, 'security/handover_qr.html', {
        'claim':      claim,
        'qr_svg':     qr_svg,
        'token_used': claim.handover_token_used,
    })


# ─── Item status override ─────────────────────────────────────────────────────

@security_required
def update_item_status(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        from .forms import ItemStatusUpdateForm
        form = ItemStatusUpdateForm(request.POST)
        if form.is_valid():
            old_status  = item.status
            item.status = form.cleaned_data['status']
            item.save()
            messages.success(
                request, f'Status changed: {old_status} → {item.status}')
    return redirect('items:detail', pk=pk)


# ─── Incidents ────────────────────────────────────────────────────────────────

@security_required
def log_incident(request, item_pk=None, claim_pk=None):
    item  = get_object_or_404(Item, pk=item_pk)   if item_pk  else None
    claim = get_object_or_404(ClaimRequest, pk=claim_pk) if claim_pk else None

    if request.method == 'POST':
        form = IncidentLogForm(request.POST)
        if form.is_valid():
            incident              = form.save(commit=False)
            incident.reported_by  = request.user
            incident.related_item = item
            incident.related_claim = claim
            if claim:
                incident.subject_user = claim.claimant
            incident.save()
            messages.success(request, 'Incident logged successfully.')
            if claim: return redirect('security:claim_detail', pk=claim.pk)
            if item:  return redirect('items:detail', pk=item.pk)
            return redirect('security:dashboard')
    else:
        form = IncidentLogForm()

    return render(request, 'security/log_incident.html',
                  {'form': form, 'item': item, 'claim': claim})


@security_required
def incident_list(request):
    incidents = IncidentLog.objects.select_related(
        'reported_by', 'subject_user', 'related_item').all()
    paginator = Paginator(incidents, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'security/incident_list.html', {'page_obj': page_obj})


# ─── Staff management ─────────────────────────────────────────────────────────

@login_required
def staff_list(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    profiles = SecurityProfile.objects.select_related('user').order_by('user__username')

    if request.method == 'POST':
        form = PromoteToSecurityForm(request.POST)
        if form.is_valid():
            user   = form.cleaned_data['user']
            badge  = form.cleaned_data['badge_number']
            office = form.cleaned_data['office_location']
            if hasattr(user, 'security_profile'):
                messages.warning(request, f'{user.username} already has a security profile.')
            else:
                SecurityProfile.objects.create(
                    user=user, badge_number=badge,
                    office_location=office, is_active=True)
                messages.success(
                    request,
                    f'✅ {user.get_full_name() or user.username} is now security staff.'
                )
            return redirect('security:staff_list')
    else:
        form = PromoteToSecurityForm()

    return render(request, 'security/staff_list.html',
                  {'profiles': profiles, 'form': form})


@login_required
def deactivate_staff(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    profile = get_object_or_404(SecurityProfile, pk=pk)
    if request.method == 'POST':
        profile.is_active = False
        profile.save()
        messages.success(
            request,
            f'{profile.user.get_full_name() or profile.user.username} deactivated.'
        )
    return redirect('security:staff_list')


@login_required
def reactivate_staff(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    profile = get_object_or_404(SecurityProfile, pk=pk)
    if request.method == 'POST':
        profile.is_active = True
        profile.save()
        messages.success(
            request,
            f'{profile.user.get_full_name() or profile.user.username} reactivated.'
        )
    return redirect('security:staff_list')


# ─── QR helper ───────────────────────────────────────────────────────────────

def _generate_qr_svg(data):
    try:
        import qrcode
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        qr      = qrcode.make(data, image_factory=factory, box_size=10)
        buf     = io.BytesIO()
        qr.save(buf)
        return buf.getvalue().decode('utf-8')
    except ImportError:
        short = str(data)[:8].upper()
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
            f'<rect width="200" height="200" fill="white" stroke="#333" stroke-width="2"/>'
            f'<rect x="10" y="10" width="60" height="60" fill="none" stroke="#333" stroke-width="4"/>'
            f'<rect x="20" y="20" width="40" height="40" fill="#333"/>'
            f'<rect x="130" y="10" width="60" height="60" fill="none" stroke="#333" stroke-width="4"/>'
            f'<rect x="140" y="20" width="40" height="40" fill="#333"/>'
            f'<rect x="10" y="130" width="60" height="60" fill="none" stroke="#333" stroke-width="4"/>'
            f'<rect x="20" y="140" width="40" height="40" fill="#333"/>'
            f'<text x="100" y="108" text-anchor="middle" font-family="monospace" font-size="11">{short}</text>'
            f'<text x="100" y="122" text-anchor="middle" font-family="monospace" font-size="8">HANDOVER TOKEN</text>'
            f'</svg>'
        )


# ─── Email notification helpers ───────────────────────────────────────────────

def _notify_security_new_claim(claim, request):
    officers = User.objects.filter(
        security_profile__is_active=True).exclude(email='')
    claimant_name = (claim.claimant.get_full_name()
                     or claim.claimant.username)
    for officer in officers:
        send_campus_email(
            subject=f'[Campus L&F] New Claim — {claim.item.title}',
            message=(
                f'Hello {officer.get_full_name() or officer.username},\n\n'
                f'A new claim has been submitted.\n\n'
                f'Item    : {claim.item.title}\n'
                f'Claimant: {claimant_name} ({claim.claimant.email})\n'
                f'Submitted: {claim.submitted_at:%d %b %Y %H:%M}\n\n'
                f'Log in to the Security Dashboard to review it.\n\n'
                f'— Campus Lost & Found'
            ),
            recipient_email=officer.email,
            email_type=EmailLog.TYPE_OTHER,
            recipient_user=officer,
        )


def _notify_claimant_approved(claim, request):
    if not claim.claimant.email:
        return False
    qr_url        = request.build_absolute_uri(
        f'/security/handover-qr/{claim.handover_token}/')
    claimant_name = (claim.claimant.get_full_name()
                     or claim.claimant.username)
    storage       = getattr(claim.item, 'custody', None)
    storage_loc   = storage.storage_location if storage else 'Security Office'

    return send_campus_email(
        subject=f'[Campus L&F] Your Claim is APPROVED — {claim.item.title}',
        message=(
            f'Hello {claimant_name},\n\n'
            f'Your claim for "{claim.item.title}" has been APPROVED.\n\n'
            f'── Collection Instructions ─────────────────\n'
            f'1. Visit the Security Office\n'
            f'   Location: {storage_loc}\n'
            f'2. Bring a valid ID (Student ID / National ID)\n'
            f'3. Show your unique QR collection code:\n'
            f'   {qr_url}\n'
            f'────────────────────────────────────────────\n\n'
            f'Keep this email private — the QR link is your collection pass.\n\n'
            f'— Campus Lost & Found Security'
        ),
        recipient_email=claim.claimant.email,
        email_type=EmailLog.TYPE_CLAIM_APPROVED,
        recipient_user=claim.claimant,
    )


def _notify_claimant_rejected(claim):
    if not claim.claimant.email:
        return False
    claimant_name = (claim.claimant.get_full_name()
                     or claim.claimant.username)
    return send_campus_email(
        subject=f'[Campus L&F] Claim Not Approved — {claim.item.title}',
        message=(
            f'Hello {claimant_name},\n\n'
            f'Unfortunately your claim for "{claim.item.title}" '
            f'was not approved.\n\n'
            f'Reason: {claim.rejection_reason}\n\n'
            f'If you believe this is an error, please visit the Security Office '
            f'in person with proof of ownership.\n\n'
            f'— Campus Lost & Found Security'
        ),
        recipient_email=claim.claimant.email,
        email_type=EmailLog.TYPE_CLAIM_REJECTED,
        recipient_user=claim.claimant,
    )


def _notify_handover_complete(handover):
    if not handover.handed_to.email:
        return
    recipient_name = (handover.handed_to.get_full_name()
                      or handover.handed_to.username)
    send_campus_email(
        subject=f'[Campus L&F] Item Collected — {handover.item.title}',
        message=(
            f'Hello {recipient_name},\n\n'
            f'This confirms that "{handover.item.title}" was collected.\n\n'
            f'── Handover Record ─────────────────────────\n'
            f'Date     : {handover.handed_over_at:%d %b %Y at %H:%M}\n'
            f'Collected: {handover.collector_name}\n'
            f'ID Number: {handover.collector_id_number}\n'
            f'QR Verified: {"Yes ✓" if handover.qr_verified else "No (manual)"}\n'
            f'────────────────────────────────────────────\n\n'
            f'— Campus Lost & Found Security'
        ),
        recipient_email=handover.handed_to.email,
        email_type=EmailLog.TYPE_HANDOVER,
        recipient_user=handover.handed_to,
    )
