from django.urls import path
from . import views

urlpatterns = [
    path('', views.session_list, name='session_list'),
    path('open/<int:table_id>/', views.open_session, name='open_session'),
    path('<int:pk>/', views.session_detail, name='session_detail'),
    path('<int:pk>/close/', views.close_session, name='close_session'),
    path('<int:pk>/merge/', views.merge_tables, name='merge_tables'),
]
