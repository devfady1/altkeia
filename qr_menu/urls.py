from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:table_uuid>/', views.qr_menu, name='qr_menu'),
    path('<uuid:table_uuid>/bill/', views.qr_bill, name='qr_bill'),
]
