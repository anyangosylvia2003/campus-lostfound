"""
Custom Django email backend that sends via Brevo HTTP API.
Set EMAIL_BACKEND=accounts.brevo_backend.BrevoEmailBackend in settings.
This intercepts ALL Django emails including password reset.
"""
import json
import urllib.request
import urllib.error
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    """
    Sends all Django emails via Brevo HTTP API.
    Works on Render free plan — no SMTP ports needed.
    """

    def send_messages(self, email_messages):
        api_key      = getattr(settings, 'BREVO_API_KEY', '').strip()
        sender_email = getattr(settings, 'EMAIL_USER', '')
        sender_name  = 'Campus Lost and Found'

        if not api_key:
            logger.error("[BrevoBackend] BREVO_API_KEY is not set!")
            return 0

        sent = 0
        for msg in email_messages:
            # Get recipients
            recipients = msg.to + msg.cc + msg.bcc
            if not recipients:
                continue

            # Get body
            body = msg.body or ''

            # Check for HTML alternative
            html_body = None
            if hasattr(msg, 'alternatives'):
                for content, mimetype in msg.alternatives:
                    if mimetype == 'text/html':
                        html_body = content
                        break

            for recipient in recipients:
                payload = {
                    'sender':      {'name': sender_name, 'email': sender_email},
                    'to':          [{'email': recipient}],
                    'subject':     msg.subject,
                    'textContent': body,
                }
                if html_body:
                    payload['htmlContent'] = html_body

                data    = json.dumps(payload).encode('utf-8')
                headers = {
                    'accept':       'application/json',
                    'content-type': 'application/json',
                    'api-key':      api_key,
                }

                try:
                    req      = urllib.request.Request(
                        'https://api.brevo.com/v3/smtp/email',
                        data=data, headers=headers, method='POST'
                    )
                    response = urllib.request.urlopen(req, timeout=15)
                    result   = json.loads(response.read().decode())
                    logger.info(
                        f"[BrevoBackend] Sent to {recipient} "
                        f"id={result.get('messageId','')}"
                    )
                    sent += 1

                except urllib.error.HTTPError as exc:
                    error = exc.read().decode() if exc.fp else str(exc)
                    logger.error(
                        f"[BrevoBackend] HTTP {exc.code} → {recipient}: {error}"
                    )
                    if not self.fail_silently:
                        raise

                except Exception as exc:
                    logger.error(
                        f"[BrevoBackend] Failed → {recipient}: {exc}"
                    )
                    if not self.fail_silently:
                        raise

        return sent
