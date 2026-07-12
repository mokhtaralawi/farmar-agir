from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('manifest.json', views.manifest_view, name='manifest'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('settings/', views.settings_view, name='settings'),
    path('warehouses/', views.warehouses_list, name='warehouses'),
    path('warehouses/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<int:pk>/edit/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouses/<int:pk>/toggle/', views.warehouse_toggle, name='warehouse_toggle'),
]
