from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'session', 'amount', 'method', 'paid_by', 'paid_at')
    list_filter = ('method',)
