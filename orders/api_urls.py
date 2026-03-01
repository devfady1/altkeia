from django.urls import path
from . import api_views

urlpatterns = [
    path('orders/', api_views.order_list_api, name='api_order_list'),
    path('orders/<int:pk>/status/', api_views.update_order_status, name='api_update_order_status'),
    path('orders/create/', api_views.create_order, name='api_create_order'),
    path('orders/kitchen/', api_views.kitchen_orders_api, name='api_kitchen_orders'),
    path('orders/<int:pk>/edit/', api_views.edit_order_items_api, name='api_edit_order_items'),
]
