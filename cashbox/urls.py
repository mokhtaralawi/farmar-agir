from django.urls import path
from . import views

app_name = 'cashbox'

urlpatterns = [
    path('', views.cashbox_list, name='list'),
    path('cash-in/', views.cash_in, name='cash_in'),
    path('cash-out/', views.cash_out, name='cash_out'),
    path('transfer/', views.transfer, name='transfer'),
    path('daily-close/', views.daily_close, name='daily_close'),
    path('transactions/<int:cashbox_id>/', views.cash_transactions, name='transactions'),
]
