from django.urls import path
from . import views

urlpatterns = [
    path('payments/<int:pk>/reprint/', views.reprint_payment, name='api_reprint_payment'),
    path('payments/<int:pk>/cancel/', views.cancel_payment, name='api_cancel_payment'),
]
