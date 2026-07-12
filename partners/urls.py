from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    path('farmers/', views.farmers_list, name='farmers'),
    path('farmers/create/', views.create_farmer, name='create_farmer'),
    path('farmers/<int:pk>/edit/', views.edit_farmer, name='edit_farmer'),
    path('buyers/', views.buyers_list, name='buyers'),
    path('buyers/create/', views.create_buyer, name='create_buyer'),
    path('buyers/<int:pk>/edit/', views.edit_buyer, name='edit_buyer'),
]
