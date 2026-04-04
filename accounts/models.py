from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class EmailLog(models.Model):
    """Audit log for every email the system attempts to send."""

    TYPE_WELCOME        = 'welcome'
    TYPE_PASSWORD_RESET = 'password_reset'
    TYPE_MATCH_ALERT    = 'match_alert'
    TYPE_CONTACT        = 'contact'
    TYPE_CLAIM_APPROVED = 'claim_approved'
    TYPE_CLAIM_REJECTED = 'claim_rejected'
    TYPE_HANDOVER       = 'handover'
    TYPE_OTHER          = 'other'
    TYPE_CHOICES = [
        (TYPE_WELCOME,        'Welcome'),
        (TYPE_PASSWORD_RESET, 'Password Reset'),
        (TYPE_MATCH_ALERT,    'Match Alert'),
        (TYPE_CONTACT,        'Contact Owner'),
        (TYPE_CLAIM_APPROVED, 'Claim Approved'),
        (TYPE_CLAIM_REJECTED, 'Claim Rejected'),
        (TYPE_HANDOVER,       'Handover Confirmation'),
        (TYPE_OTHER,          'Other'),
    ]

    STATUS_SENT   = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_SENT,   'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    recipient       = models.EmailField()
    recipient_user  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='email_logs'
    )
    subject         = models.CharField(max_length=300)
    email_type      = models.CharField(max_length=30, choices=TYPE_CHOICES,
                                       default=TYPE_OTHER, db_index=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                       default=STATUS_SENT, db_index=True)
    error_message   = models.TextField(blank=True)
    sent_at         = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.get_email_type_display()} → {self.recipient}"
