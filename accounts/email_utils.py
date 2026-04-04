"""
Centralised email utility — Campus Lost & Found.

All emails go through send_campus_email() which:
  - Uses Django's send_mail() (Gmail SMTP in production, console in dev)
  - Logs every attempt to EmailLog
  - Returns True on success, False on failure
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_campus_email(subject, message, recipient_email,
                      email_type='other', recipient_user=None,
                      html_message=None):
    """
    Send a plain-text (+ optional HTML) email and log the attempt.

    Args:
        subject         : Email subject line
        message         : Plain-text body
        recipient_email : Recipient address string
        email_type      : One of EmailLog.TYPE_* constants
        recipient_user  : Django User instance (optional, for log linkage)
        html_message    : HTML version of the body (optional)

    Returns:
        True on success, False on failure.
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
        logger.info(f"[EMAIL:{email_type}] Sent to {recipient_email}")
        return True

    except Exception as exc:
        log.status = EmailLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save()
        logger.error(f"[EMAIL:{email_type}] Failed to {recipient_email}: {exc}")
        return False
