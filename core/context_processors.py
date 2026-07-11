"""
Context Processors - System-wide template context
"""

from .models import SystemSettings


def system_info(request):
    """Provide system settings to all templates"""
    try:
        settings = SystemSettings.get_settings()
        return {
            'system_name': settings.company_name or 'نظام البيع للمجابرة',
            'company_name': settings.company_name,
            'company_phone': settings.phone or '',
            'company_email': settings.email or '',
        }
    except Exception:
        return {
            'system_name': 'نظام البيع للمجابرة',
            'company_name': 'نظام البيع للمجابرة',
            'company_phone': '',
            'company_email': '',
        }
