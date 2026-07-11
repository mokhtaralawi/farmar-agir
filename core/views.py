"""
Core Views - Views for core app
"""

import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SystemSettings


def manifest_view(request):
    """PWA Manifest"""
    manifest = {
        "name": "نظام البيع للمجابرة",
        "short_name": "نظام البيع للقات",
        "description": "نظام ERP لبيع القات بالجملة للمجابرة",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#F5F5F5",
        "theme_color": "#2E7D32",
        "orientation": "portrait",
        "icons": [
            {"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return JsonResponse(manifest)


def service_worker(request):
    """PWA Service Worker"""
    sw_code = """
const CACHE_NAME = 'agri-bridge-v1';
const urlsToCache = ['/'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
});
"""
    return HttpResponse(sw_code, content_type='application/javascript')


@login_required
def settings_view(request):
    """System Settings"""
    if request.method == 'POST':
        settings = SystemSettings.get_settings()
        settings.company_name = request.POST.get('company_name', settings.company_name)
        settings.company_phone = request.POST.get('company_phone', settings.company_phone)
        settings.company_email = request.POST.get('company_email', settings.company_email)
        settings.company_address = request.POST.get('company_address', settings.company_address)
        settings.default_currency = request.POST.get('default_currency', settings.default_currency)
        settings.default_commission_rate = float(request.POST.get('default_commission_rate', 5))
        settings.default_language = request.POST.get('default_language', settings.default_language)
        settings.invoice_prefix = request.POST.get('invoice_prefix', settings.invoice_prefix)
        settings.save()
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('core:settings')
    
    settings = SystemSettings.get_settings()
    return render(request, 'settings.html', {'settings': settings})
