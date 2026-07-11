from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    path('', views.journal_entries, name='entries'),
    path('create/', views.create_entry, name='create'),
    path('entry/<int:pk>/', views.entry_detail, name='entry_detail'),
    path('ledger/', views.ledger, name='ledger'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('chart/', views.account_chart, name='chart'),
    path('close-period/', views.close_period, name='close_period'),
]
