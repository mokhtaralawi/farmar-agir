from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payments_list, name='list'),
    path('create/', views.create_payment, name='create'),
    path('print/<int:pk>/', views.print_payment, name='print'),
    path('farmer-statement/<int:farmer_id>/', views.farmer_statement, name='farmer_statement'),
    path('settlements/', views.settlements_list, name='settlements'),
    path('settlements/create/', views.create_settlement, name='create_settlement'),
]
