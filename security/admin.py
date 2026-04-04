from django.contrib import admin
from .models import SecurityProfile, CustodyRecord, ClaimRequest, HandoverLog, IncidentLog, CustodyTransferLog


@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge_number', 'office_location', 'is_active']
    list_filter = ['is_active']
    search_fields = ['user__username', 'badge_number']


class CustodyTransferInline(admin.TabularInline):
    model = CustodyTransferLog
    extra = 0
    readonly_fields = ['transferred_at', 'transferred_by']


@admin.register(CustodyRecord)
class CustodyRecordAdmin(admin.ModelAdmin):
    list_display = ['item', 'custody_status', 'storage_location', 'received_at', 'retention_deadline', 'received_by']
    list_filter = ['custody_status']
    search_fields = ['item__title']
    inlines = [CustodyTransferInline]


@admin.register(ClaimRequest)
class ClaimRequestAdmin(admin.ModelAdmin):
    list_display = ['item', 'claimant', 'status', 'submitted_at', 'reviewed_by', 'handover_token_used']
    list_filter = ['status']
    search_fields = ['item__title', 'claimant__username']
    readonly_fields = ['handover_token']


@admin.register(HandoverLog)
class HandoverLogAdmin(admin.ModelAdmin):
    list_display = ['item', 'collector_name', 'collector_id_number', 'handed_over_at', 'qr_verified', 'handed_over_by']
    readonly_fields = ['handed_over_at']


@admin.register(IncidentLog)
class IncidentLogAdmin(admin.ModelAdmin):
    list_display = ['incident_type', 'severity', 'reported_by', 'subject_user', 'related_item', 'created_at']
    list_filter = ['incident_type', 'severity']


@admin.register(CustodyTransferLog)
class CustodyTransferLogAdmin(admin.ModelAdmin):
    list_display = ['custody', 'from_location', 'to_location', 'transferred_by', 'transferred_at']
    readonly_fields = ['transferred_at']
