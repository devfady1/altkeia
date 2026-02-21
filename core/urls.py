from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('manage/', views.manage_view, name='manage'),
    path('manage/floors/', views.manage_floors, name='manage_floors'),
    path('manage/tables/', views.manage_tables, name='manage_tables'),
    path('manage/products/', views.manage_products, name='manage_products'),
    path('manage/devices/', views.manage_devices, name='manage_devices'),
    path('manage/employees/', views.manage_employees, name='manage_employees'),
]
