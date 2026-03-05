from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_dashboard, name='inventory_dashboard'),
    path('item/<int:item_id>/', views.inventory_item_detail, name='inventory_item_detail'),
    path('product-ingredients/', views.product_ingredients_view, name='product_ingredients'),
    path('shift-report/', views.shift_inventory_report, name='shift_inventory_report'),
]
