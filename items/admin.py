from django.contrib import admin
from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'item_type', 'category', 'status', 'brand', 'color', 'location', 'date', 'owner', 'created_at']
    list_filter = ['item_type', 'category', 'status', 'location']
    search_fields = ['title', 'description', 'brand', 'color', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    actions = ['mark_resolved', 'mark_donated']

    def mark_resolved(self, request, queryset):
        queryset.update(status=Item.STATUS_RESOLVED)
    mark_resolved.short_description = 'Mark selected items as Resolved'

    def mark_donated(self, request, queryset):
        queryset.update(status=Item.STATUS_DONATED)
    mark_donated.short_description = 'Mark selected items as Donated/Disposed'
