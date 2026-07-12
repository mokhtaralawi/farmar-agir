"""
Core Views - Views for core app
"""

import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SystemSettings, Warehouse, Branch, ActivityLog


def manifest_view(request):
    """PWA Manifest"""
    manifest = {
        "name": "نظام المجابرة",
        "short_name": "نظام المجابرة",
        "description": "نظام إدارة سوق الخضروات والفواكه بالجملة",
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


@login_required
def warehouses_list(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول')
        return redirect('reports:dashboard')
    warehouses = Warehouse.objects.select_related('branch').order_by('-created_at')
    return render(request, 'core/warehouses.html', {'warehouses': warehouses})


@login_required
def warehouse_create(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول')
        return redirect('reports:dashboard')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'اسم المخزن مطلوب')
        else:
            Warehouse.objects.create(
                name=name,
                name_en=request.POST.get('name_en', '').strip(),
                branch_id=request.POST.get('branch') or None,
                is_default=request.POST.get('is_default') == 'on',
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, f'تم إنشاء مخزن "{name}" بنجاح')
            return redirect('core:warehouses')
    return render(request, 'core/warehouse_form.html', {
        'branches': Branch.objects.filter(is_active=True),
        'mode': 'create',
    })


@login_required
def warehouse_edit(request, pk):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول')
        return redirect('reports:dashboard')
    warehouse = get_object_or_404(Warehouse, id=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'اسم المخزن مطلوب')
        else:
            warehouse.name = name
            warehouse.name_en = request.POST.get('name_en', '').strip()
            warehouse.branch_id = request.POST.get('branch') or None
            warehouse.is_default = request.POST.get('is_default') == 'on'
            warehouse.is_active = request.POST.get('is_active') == 'on'
            warehouse.save()
            messages.success(request, f'تم تحديث مخزن "{name}" بنجاح')
            return redirect('core:warehouses')
    return render(request, 'core/warehouse_form.html', {
        'warehouse': warehouse,
        'branches': Branch.objects.filter(is_active=True),
        'mode': 'edit',
    })


@login_required
def warehouse_toggle(request, pk):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول')
        return redirect('reports:dashboard')
    warehouse = get_object_or_404(Warehouse, id=pk)
    warehouse.is_active = not warehouse.is_active
    warehouse.save()
    status = 'تفعيل' if warehouse.is_active else 'تعطيل'
    messages.success(request, f'تم {status} مخزن "{warehouse.name}"')
    return redirect('core:warehouses')


@login_required
def activity_log(request):
    """سجل النشاطات - للمدير فقط"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول')
        return redirect('reports:dashboard')

    logs = ActivityLog.objects.select_related('user').all()

    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    logs = logs[:200]

    from accounts.models import User
    return render(request, 'core/activity_log.html', {
        'logs': logs,
        'action_choices': ActivityLog.ACTION_CHOICES,
        'users': User.objects.filter(is_active=True),
        'filters': {'action': action_filter, 'user': user_filter, 'date_from': date_from, 'date_to': date_to},
    })
