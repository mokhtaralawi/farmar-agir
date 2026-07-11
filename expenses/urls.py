from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expenses_list, name='list'),
    path('create/', views.create_expense, name='create'),
]
