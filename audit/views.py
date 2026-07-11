"""
Audit Views - سجل التدقيق
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AuditLog


@login_required
def audit_logs(request):
    logs = AuditLog.objects.all().select_related('user').order_by('-created_at')[:100]
    return render(request, 'audit/logs.html', {'logs': logs})
