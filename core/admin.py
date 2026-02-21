from django.contrib import admin
from .models import Floor, SystemSettings

@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_editable = ('order', 'is_active')

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    pass
