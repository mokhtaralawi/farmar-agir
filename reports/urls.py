from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sales/', views.sales_report, name='sales'),
    path('receiving/', views.receiving_report, name='receiving'),
    path('inventory/', views.inventory_report, name='inventory'),
    path('financial/', views.financial_report, name='financial'),
    path('profit-loss/', views.profit_loss, name='profit_loss'),
]
