"""
Custom password reset email sender that uses Brevo API instead of SMTP.
Plugged into Django's PasswordResetForm via the email_template_name approach.
"""
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings


class BrevoPasswordResetForm(PasswordResetForm):
    """
    Extends Django's PasswordResetForm to send via Brevo API
    instead of Django's SMTP backend.
    """

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        from accounts.email_utils import send_campus_email
        from accounts.models import EmailLog
        from django.template import loader

        subject = loader.render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body    = loader.render_to_string(email_template_name, context)

        send_campus_email(
            subject=subject,
            message=body,
            recipient_email=to_email,
            email_type=EmailLog.TYPE_PASSWORD_RESET,
        )
