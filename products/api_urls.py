from django.urls import path
from . import api_views

urlpatterns = [
    path('products/', api_views.products_list_api, name='api_products_list'),
]
