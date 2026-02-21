from django.contrib import admin
from .models import Table

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'floor', 'number', 'status', 'capacity', 'is_active')
    list_filter = ('floor', 'status', 'is_active')
    list_editable = ('status',)
