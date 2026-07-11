from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.products_list, name='products'),
    path('create/', views.create_product, name='create'),
    path('prices/<int:pk>/', views.product_prices, name='prices'),
]
