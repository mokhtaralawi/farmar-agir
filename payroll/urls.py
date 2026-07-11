from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    path('employees/', views.employees_list, name='employees'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('payrolls/', views.payrolls_list, name='payrolls'),
    path('payrolls/create/', views.create_payroll, name='create_payroll'),
    path('advances/', views.advances_list, name='advances'),
    path('advances/create/', views.create_advance, name='create_advance'),
    path('attendance/', views.attendance_list, name='attendance'),
]
