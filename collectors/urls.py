from django.urls import path
from . import views

app_name = 'collectors'

urlpatterns = [
    path('', views.collectors_list, name='list'),
    path('create/', views.create_collection, name='create'),
    path('print/<int:pk>/', views.print_collection, name='print'),
    path('buyer-statement/<int:buyer_id>/', views.buyer_statement, name='buyer_statement'),
]
