from django.contrib import admin
from .models import TableSession

@admin.register(TableSession)
class TableSessionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'primary_table', 'status', 'opened_at', 'total_amount')
    list_filter = ('status',)
