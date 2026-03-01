from django.urls import path
from django.contrib.auth import views as auth_views
from . import staff_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('manage/employees/<int:pk>/', staff_views.employee_detail, name='employee_detail'),
    path('api/staff/order/add/', staff_views.add_staff_order, name='add_staff_order'),
    path('api/staff/advance/add/', staff_views.add_staff_advance, name='add_staff_advance'),
    path('api/staff/order/<int:pk>/delete/', staff_views.delete_staff_order, name='delete_staff_order'),
    path('api/staff/advance/<int:pk>/delete/', staff_views.delete_staff_advance, name='delete_staff_advance'),
    path('api/staff/salary/update/', staff_views.update_employee_salary, name='update_employee_salary'),
]

