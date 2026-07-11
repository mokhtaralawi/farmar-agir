from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('dashboard/', views.dashboard_data, name='dashboard_data'),
    path('receiving/', views.receiving_list, name='receiving'),
    path('billing/', views.billing_list, name='billing'),
    path('inventory/', views.inventory_data, name='inventory'),
    path('farmers/', views.farmers_list, name='farmers'),
    path('buyers/', views.buyers_list, name='buyers'),
]
