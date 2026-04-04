import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from items.models import Item


class SecurityProfile(models.Model):
    """Marks a user as a security staff member with extra privileges."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_profile')
    badge_number = models.CharField(max_length=50, unique=True)
    office_location = models.CharField(max_length=200, default='Main Security Office')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Security: {self.user.get_full_name() or self.user.username} ({self.badge_number})"


class CustodyRecord(models.Model):
    """Tracks when a found item is physically received by the security office."""
    STATUS_IN_CUSTODY = 'in_custody'
    STATUS_CLAIMED = 'claimed'
    STATUS_RETURNED = 'returned'
    STATUS_DISPOSED = 'disposed'
    STATUS_CHOICES = [
        (STATUS_IN_CUSTODY, 'In Custody'),
        (STATUS_CLAIMED, 'Claimed — Pending Handover'),
        (STATUS_RETURNED, 'Returned to Owner'),
        (STATUS_DISPOSED, 'Disposed / Donated'),
    ]

    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='custody')
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='custody_received'
    )
    received_at = models.DateTimeField(default=timezone.now)
    storage_location = models.CharField(max_length=200, default='Security Office — Main Cabinet')
    custody_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_CUSTODY, db_index=True)
    notes = models.TextField(blank=True)
    secret_identifiers = models.TextField(
        blank=True,
        help_text="Hidden details: serial numbers, contents, personal marks. NOT shown publicly."
    )
    # Retention tracking
    retention_deadline = models.DateField(
        null=True, blank=True,
        help_text="Date after which the item should be reviewed for donation/disposal."
    )

    class Meta:
        ordering = ['-received_at']

    def save(self, *args, **kwargs):
        # Auto-set retention deadline from item's retention_days if not set
        if not self.retention_deadline and self.item_id:
            from datetime import timedelta
            days = getattr(self.item, 'retention_days', 60)
            self.retention_deadline = (self.received_at or timezone.now()).date() + timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.custody_status in (self.STATUS_RETURNED, self.STATUS_DISPOSED):
            return False
        return self.retention_deadline and timezone.now().date() > self.retention_deadline

    @property
    def days_until_deadline(self):
        if not self.retention_deadline:
            return None
        return (self.retention_deadline - timezone.now().date()).days

    def __str__(self):
        return f"Custody: {self.item.title} [{self.get_custody_status_display()}]"


class ClaimRequest(models.Model):
    """A user's formal request to claim a found item held by security."""
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='claim_requests')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claim_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    proof_description = models.TextField(
        help_text="Claimant's detailed description of the item (color, brand, marks, contents)."
    )
    proof_identifiers = models.TextField(
        help_text="Unique identifiers: serial number, name tag, contents of wallet, etc."
    )
    additional_notes = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='claims_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    security_notes = models.TextField(blank=True)

    # QR handover token — generated on approval, single-use
    handover_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    handover_token_used = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = [('item', 'claimant')]

    def __str__(self):
        return f"Claim by {self.claimant.username} for '{self.item.title}' [{self.get_status_display()}]"


class HandoverLog(models.Model):
    """Permanent audit log of every physical item handover."""
    claim = models.OneToOneField(ClaimRequest, on_delete=models.CASCADE, related_name='handover')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='handovers')
    handed_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='handovers_received')

    collector_name = models.CharField(max_length=200)
    collector_id_number = models.CharField(max_length=100)
    collector_id_type = models.CharField(
        max_length=50,
        choices=[('student_id', 'Student ID'), ('staff_id', 'Staff ID'),
                 ('national_id', 'National ID'), ('other', 'Other')],
        default='student_id'
    )
    handed_over_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='handovers_given'
    )
    handed_over_at = models.DateTimeField(default=timezone.now)
    # Whether this handover was verified via QR scan
    qr_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-handed_over_at']

    def __str__(self):
        return f"Handover: {self.item.title} → {self.collector_name} on {self.handed_over_at:%Y-%m-%d}"


class CustodyTransferLog(models.Model):
    """Chain-of-custody: every time an item moves between locations."""
    custody = models.ForeignKey(CustodyRecord, on_delete=models.CASCADE, related_name='transfers')
    transferred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='custody_transfers')
    from_location = models.CharField(max_length=200)
    to_location = models.CharField(max_length=200)
    transferred_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-transferred_at']

    def __str__(self):
        return f"{self.custody.item.title}: {self.from_location} → {self.to_location}"


class IncidentLog(models.Model):
    """Log of suspicious activity, false claims, misuse."""
    SEVERITY_LOW = 'low'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_HIGH = 'high'
    SEVERITY_CHOICES = [(SEVERITY_LOW, 'Low'), (SEVERITY_MEDIUM, 'Medium'), (SEVERITY_HIGH, 'High')]

    TYPE_FALSE_CLAIM = 'false_claim'
    TYPE_SPAM = 'spam'
    TYPE_SUSPICIOUS = 'suspicious'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_FALSE_CLAIM, 'False Claim'),
        (TYPE_SPAM, 'Spam / Fake Post'),
        (TYPE_SUSPICIOUS, 'Suspicious Activity'),
        (TYPE_OTHER, 'Other'),
    ]

    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='incidents_reported')
    subject_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents_against')
    related_item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    related_claim = models.ForeignKey(ClaimRequest, on_delete=models.SET_NULL, null=True, blank=True)
    incident_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default=SEVERITY_LOW)
    description = models.TextField()
    action_taken = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.get_incident_type_display()} — {self.created_at:%Y-%m-%d}"
