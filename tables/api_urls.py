from django.urls import path
from . import api_views

urlpatterns = [
    path('tables/status/', api_views.tables_status, name='api_tables_status'),
    path('tables/<int:pk>/update-status/', api_views.update_table_status, name='api_update_table_status'),
]
