from django.urls import path
from . import views

urlpatterns = [
    path('', views.queue_list, name='queue_list'),
    path('join/', views.join_queue, name='join_queue'),
    path('<int:pk>/cancel/', views.cancel_queue, name='cancel_queue'),
    path('<int:pk>/activate/', views.activate_queue, name='activate_queue'),
]
