from django.urls import path
from . import api_views

urlpatterns = [
    path('queue/status/', api_views.queue_status_api, name='api_queue_status'),
    path('queue/join/', api_views.join_queue_api, name='api_join_queue'),
    path('queue/<int:pk>/cancel/', api_views.cancel_queue_api, name='api_cancel_queue'),
]
