from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports'),
    path('daily/', views.daily_report, name='daily_report'),
    path('monthly/', views.monthly_report, name='monthly_report'),
]
