from django.urls import path
from . import views

urlpatterns = [
    path('', views.activity_list, name='activity_list'),
    path('start/', views.start_activity, name='start_activity'),
    path('<int:pk>/end/', views.end_activity, name='end_activity'),
]
