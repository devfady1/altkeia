from django.contrib import admin
from .models import QueueEntry

@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'activity_type', 'position', 'status', 'created_at')
    list_filter = ('activity_type', 'status')
