from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('kitchen/', views.kitchen_view, name='kitchen'),
]
