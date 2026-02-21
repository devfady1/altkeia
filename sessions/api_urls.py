from django.urls import path
from . import api_views

urlpatterns = [
    path('sessions/<int:pk>/', api_views.session_detail_api, name='api_session_detail'),
    path('sessions/<int:pk>/close/', api_views.close_session_api, name='api_close_session'),
    path('sessions/<int:pk>/merge/', api_views.merge_tables_api, name='api_merge_tables'),
    path('sessions/by-table/<int:table_id>/', api_views.session_by_table_api, name='api_session_by_table'),
]
