from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


CAMPUS_LOCATIONS = [
    ('', 'Select a location...'),
    ('Main Gate', 'Main Gate'),
    ('Library', 'Library'),
    ('Student Centre', 'Student Centre'),
    ('Cafeteria / Dining Hall', 'Cafeteria / Dining Hall'),
    ('Admin Block', 'Admin Block'),
    ('Science Block', 'Science Block'),
    ('Engineering Block', 'Engineering Block'),
    ('Arts Block', 'Arts Block'),
    ('Business Block', 'Business Block'),
    ('ICT Lab', 'ICT Lab'),
    ('Sports Complex / Field', 'Sports Complex / Field'),
    ('Gym', 'Gym'),
    ('Auditorium / Hall', 'Auditorium / Hall'),
    ('Chapel / Prayer Room', 'Chapel / Prayer Room'),
    ('Health Centre / Clinic', 'Health Centre / Clinic'),
    ('Hostel Block A', 'Hostel Block A'),
    ('Hostel Block B', 'Hostel Block B'),
    ('Hostel Block C', 'Hostel Block C'),
    ('Parking Lot', 'Parking Lot'),
    ('Bus / Matatu Stage', 'Bus / Matatu Stage'),
    ('ATM / Finance Office', 'ATM / Finance Office'),
    ('Lecture Hall 1', 'Lecture Hall 1'),
    ('Lecture Hall 2', 'Lecture Hall 2'),
    ('Lecture Hall 3', 'Lecture Hall 3'),
    ('Other / Unknown', 'Other / Unknown'),
]


class Item(models.Model):
    TYPE_LOST = 'lost'
    TYPE_FOUND = 'found'
    TYPE_CHOICES = [
        (TYPE_LOST, 'Lost'),
        (TYPE_FOUND, 'Found'),
    ]

    CAT_ELECTRONICS = 'electronics'
    CAT_DOCUMENTS = 'documents'
    CAT_CLOTHING = 'clothing'
    CAT_KEYS = 'keys'
    CAT_IDS = 'ids'
    CAT_WALLETS = 'wallets'
    CAT_BAGS = 'bags'
    CAT_OTHERS = 'others'
    CATEGORY_CHOICES = [
        (CAT_ELECTRONICS, 'Electronics'),
        (CAT_DOCUMENTS, 'Documents / Certificates'),
        (CAT_IDS, 'ID / Student Card'),
        (CAT_KEYS, 'Keys'),
        (CAT_WALLETS, 'Wallet / Purse'),
        (CAT_BAGS, 'Bag / Backpack'),
        (CAT_CLOTHING, 'Clothing'),
        (CAT_OTHERS, 'Others'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_MATCHED = 'matched'
    STATUS_CLAIMED = 'claimed'
    STATUS_RESOLVED = 'resolved'
    STATUS_DONATED = 'donated'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_MATCHED, 'Matched'),
        (STATUS_CLAIMED, 'Claimed — Pending Verification'),
        (STATUS_RESOLVED, 'Resolved / Returned'),
        (STATUS_DONATED, 'Donated / Disposed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    item_type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)

    # New structured fields
    brand = models.CharField(max_length=100, blank=True, help_text='e.g. Samsung, HP, Nike')
    color = models.CharField(max_length=100, blank=True, help_text='e.g. Black, Blue, Red/White')
    location = models.CharField(max_length=200, choices=CAMPUS_LOCATIONS, db_index=True)
    location_detail = models.CharField(
        max_length=200, blank=True,
        help_text='Extra detail, e.g. "near the window on floor 2"'
    )
    date = models.DateField()
    time_of_day = models.TimeField(null=True, blank=True, help_text='Approximate time (optional)')

    image = models.ImageField(upload_to='items/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Retention: track when item should be reviewed for disposal
    retention_days = models.PositiveIntegerField(default=60, help_text='Days to hold before disposal review')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item_type', 'category', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.get_item_type_display()}] {self.title}"

    def get_absolute_url(self):
        return reverse('items:detail', kwargs={'pk': self.pk})

    @property
    def is_overdue_for_review(self):
        """True if a found item has been held past its retention period."""
        if self.item_type != self.TYPE_FOUND:
            return False
        if self.status in (self.STATUS_RESOLVED, self.STATUS_DONATED):
            return False
        delta = (timezone.now().date() - self.date)
        return delta.days >= self.retention_days

    @property
    def days_held(self):
        return (timezone.now().date() - self.date).days

    def get_match_score(self, other):
        """
        Return a 0–100 score of how well `other` matches this item.
        Items must be opposite types and same category to score at all.
        """
        if other.item_type == self.item_type:
            return 0
        if other.category != self.category:
            return 0

        score = 0
        max_score = 0

        stop_words = {
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of',
            'and', 'or', 'is', 'was', 'my', 'i', 'it', 'with', 'have'
        }

        def words(text):
            return set(text.lower().split()) - stop_words

        # Title keyword overlap (weight 4)
        tw1 = words(self.title)
        tw2 = words(other.title)
        if tw1 and tw2:
            overlap = len(tw1 & tw2) / max(len(tw1), len(tw2))
            score += overlap * 4
        max_score += 4

        # Description keyword overlap (weight 3)
        dw1 = words(self.description)
        dw2 = words(other.description)
        if dw1 and dw2:
            overlap = len(dw1 & dw2) / max(len(dw1), len(dw2))
            score += overlap * 3
        max_score += 3

        # Brand match (weight 2) — case-insensitive
        if self.brand and other.brand:
            if self.brand.lower().strip() == other.brand.lower().strip():
                score += 2
        max_score += 2

        # Color overlap (weight 2)
        if self.color and other.color:
            c1 = words(self.color)
            c2 = words(other.color)
            if c1 & c2:
                score += 2
        max_score += 2

        # Same location (weight 2)
        if self.location and other.location and self.location == other.location:
            score += 2
        max_score += 2

        # Date proximity (weight 1) — within 7 days scores full, 30 days scores half
        if self.date and other.date:
            diff = abs((self.date - other.date).days)
            if diff <= 7:
                score += 1
            elif diff <= 30:
                score += 0.5
        max_score += 1

        if max_score == 0:
            return 0
        return round((score / max_score) * 100)

    def get_matches(self, limit=5, min_score=0):
        """Find possible matches with percentage scores."""
        opposite_type = self.TYPE_FOUND if self.item_type == self.TYPE_LOST else self.TYPE_LOST
        candidates = Item.objects.filter(
            item_type=opposite_type,
            category=self.category,
            status__in=[self.STATUS_ACTIVE, self.STATUS_MATCHED],
        ).exclude(pk=self.pk).select_related('owner')

        scored = []
        for item in candidates:
            s = self.get_match_score(item)
            if s > min_score:
                scored.append((s, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [(score, item) for score, item in scored[:limit]]

    def get_strong_matches(self, threshold=70):
        """Return matches at or above the given percentage threshold."""
        return [(s, item) for s, item in self.get_matches(limit=20) if s >= threshold]
