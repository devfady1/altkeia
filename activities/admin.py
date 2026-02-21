from django.contrib import admin
from .models import ActivityType, Device, ActivitySession

@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_hour', 'icon', 'is_active')

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'activity_type', 'status', 'is_active')
    list_filter = ('activity_type', 'status')

@admin.register(ActivitySession)
class ActivitySessionAdmin(admin.ModelAdmin):
    list_display = ('device', 'session', 'started_at', 'ended_at', 'total_price')
