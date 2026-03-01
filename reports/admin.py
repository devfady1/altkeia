from django.contrib import admin
from .models import CashierShift


@admin.register(CashierShift)
class CashierShiftAdmin(admin.ModelAdmin):
    list_display = ('pk', 'started_by', 'started_at', 'ended_at', 'is_active', 'total_revenue')
    list_filter = ('is_active',)
    readonly_fields = ('total_revenue', 'total_orders', 'total_sessions', 'total_discount')
