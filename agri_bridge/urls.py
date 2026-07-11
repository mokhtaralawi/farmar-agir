"""
Main URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('dashboard/', include('reports.urls')),
    path('partners/', include('partners.urls')),
    path('products/', include('products.urls')),
    path('inventory/', include('inventory.urls')),
    path('receiving/', include('receiving.urls')),
    path('billing/', include('billing.urls')),
    path('collectors/', include('collectors.urls')),
    path('payments/', include('payments.urls')),
    path('cashbox/', include('cashbox.urls')),
    path('expenses/', include('expenses.urls')),
    path('accounting/', include('accounting.urls')),
    path('payroll/', include('payroll.urls')),
    path('audit/', include('audit.urls')),
    path('api/', include('api.urls')),
    path('core/', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
