from django.contrib import admin
from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display  = ['recipient', 'email_type', 'status', 'subject', 'sent_at']
    list_filter   = ['status', 'email_type']
    search_fields = ['recipient', 'subject']
    readonly_fields = ['sent_at']
    ordering = ['-sent_at']
