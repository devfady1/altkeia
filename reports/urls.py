from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports'),
    path('monthly/', views.monthly_report, name='monthly_report'),
    path('shift/<int:pk>/', views.shift_report, name='shift_report'),
    path('shift/<int:pk>/print/', views.print_shift_report_api, name='print_shift_report_api'),
    path('shift/start/', views.start_shift, name='start_shift'),
    path('shift/end/', views.end_shift, name='end_shift'),
    path('shift/status/', views.shift_status, name='shift_status'),
    path('invoices/', views.invoice_list, name='invoice_list'),
]
