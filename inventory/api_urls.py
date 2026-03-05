from django.urls import path
from . import views

urlpatterns = [
    path('inventory/stock/add/', views.add_stock_api, name='api_add_stock'),
]
