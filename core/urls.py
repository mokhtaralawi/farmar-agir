from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('manifest.json', views.manifest_view, name='manifest'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('settings/', views.settings_view, name='settings'),
]
