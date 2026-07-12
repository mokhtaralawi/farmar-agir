from django.urls import path
from . import views

app_name = 'receiving'

urlpatterns = [
    path('', views.receiving_list, name='list'),
    path('create/', views.create_receiving, name='create'),
    path('print/<int:pk>/', views.print_receiving, name='print'),
    path('detail/<int:pk>/', views.receiving_detail, name='detail'),
    path('edit/<int:pk>/', views.edit_receiving, name='edit'),
]
