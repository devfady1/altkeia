from django.urls import path
from . import views

urlpatterns = [
    path('pay/<int:session_id>/', views.process_payment, name='process_payment'),
]
