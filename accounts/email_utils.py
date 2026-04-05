"""
Centralised email utility — Campus Lost & Found.
Uses Brevo HTTP API in production (works on Render free plan).
Falls back to console in development.
"""
import logging
import json
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)


def send_campus_email(subject, message, recipient_email,
                      email_type='other', recipient_user=None,
                      html_message=None):
    """
    Send an email and log the attempt.
    Returns True on success, False on failure.
    """
    from accounts.models import EmailLog

    if not recipient_email:
        logger.warning(f"send_campus_email: no recipient for type={email_type}")
        return False

    log = EmailLog(
        recipient=recipient_email,
        recipient_user=recipient_user,
        subject=subject,
        email_type=email_type,
        status=EmailLog.STATUS_SENT,
    )

    brevo_api_key = getattr(settings, 'BREVO_API_KEY', '').strip()
    debug         = getattr(settings, 'DEBUG', False)

    logger.info(f"[EMAIL] type={email_type} to={recipient_email} "
                f"debug={debug} brevo_key_set={bool(brevo_api_key)}")

    # ── Use Brevo API if key is available (works in both dev and prod) ────────
    if brevo_api_key:
        return _send_via_brevo(subject, message, recipient_email,
                               html_message, log, brevo_api_key)

    # ── Development fallback: console backend ─────────────────────────────────
    if debug:
        from django.core.mail import send_mail
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            log.status = EmailLog.STATUS_SENT
            log.save()
            logger.info(f"[EMAIL:console] {email_type} → {recipient_email}")
            return True
        except Exception as exc:
            log.status = EmailLog.STATUS_FAILED
            log.error_message = str(exc)
            log.save()
            logger.error(f"[EMAIL:console] Failed → {recipient_email}: {exc}")
            return False

    # ── Production fallback: SMTP ─────────────────────────────────────────────
    from django.core.mail import send_mail
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        log.status = EmailLog.STATUS_SENT
        log.save()
        logger.info(f"[EMAIL:smtp] {email_type} → {recipient_email}")
        return True
    except Exception as exc:
        log.status = EmailLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save()
        logger.error(f"[EMAIL:smtp] Failed → {recipient_email}: {exc}")
        return False


def _send_via_brevo(subject, message, recipient_email,
                    html_message, log, api_key):
    """Send via Brevo HTTP API — no SMTP, works on Render free plan."""
    sender_email = getattr(settings, 'EMAIL_USER', '')
    sender_name  = 'Campus Lost and Found'

    payload = {
        'sender':      {'name': sender_name, 'email': sender_email},
        'to':          [{'email': recipient_email}],
        'subject':     subject,
        'textContent': message,
    }
    if html_message:
        payload['htmlContent'] = html_message

    data    = json.dumps(payload).encode('utf-8')
    headers = {
        'accept':        'application/json',
        'content-type':  'application/json',
        'api-key':       api_key,
    }

    try:
        req      = urllib.request.Request(
            'https://api.brevo.com/v3/smtp/email',
            data=data, headers=headers, method='POST'
        )
        response = urllib.request.urlopen(req, timeout=15)
        body     = json.loads(response.read().decode())
        log.provider_message_id = body.get('messageId', '')
        log.status = EmailLog.STATUS_SENT
        log.save()
        logger.info(f"[EMAIL:brevo] Sent to {recipient_email} "
                    f"id={log.provider_message_id}")
        return True

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else str(exc)
        log.status = EmailLog.STATUS_FAILED
        log.error_message = f"Brevo {exc.code}: {error_body}"
        log.save()
        logger.error(f"[EMAIL:brevo] HTTP error → {recipient_email}: "
                     f"{log.error_message}")
        return False

    except Exception as exc:
        log.status = EmailLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save()
        logger.error(f"[EMAIL:brevo] Failed → {recipient_email}: {exc}")
        return False
