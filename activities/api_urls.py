from django.urls import path
from . import api_views

urlpatterns = [
    path('activities/start/', api_views.start_activity_api, name='api_start_activity'),
    path('activities/<int:pk>/end/', api_views.end_activity_api, name='api_end_activity'),
    path('activities/devices/', api_views.devices_status_api, name='api_devices_status'),
]
