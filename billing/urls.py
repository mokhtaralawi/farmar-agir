from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.sales_list, name='list'),
    path('create/', views.create_sale, name='create'),
    path('print/<int:pk>/', views.print_sale, name='print'),
    path('edit/<int:pk>/', views.edit_sale, name='edit'),
]
