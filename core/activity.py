"""
Activity Log utility - سجل النشاطات
"""
from core.models import ActivityLog


def log_activity(request, action, description, reference_type='', reference_id=None):
    """تسجيل نشاط"""
    ip = None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        ip = x_forwarded.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    user = request.user if request.user.is_authenticated else None
    ActivityLog.objects.create(
        user=user, action=action, description=description,
        reference_type=reference_type, reference_id=reference_id, ip_address=ip,
    )
