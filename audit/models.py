"""
Audit application models - سجل العمليات
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """سجل العمليات"""
    ACTION_TYPES = [
        ('CREATE', _('إنشاء')),
        ('UPDATE', _('تعديل')),
        ('DELETE', _('حذف')),
        ('APPROVE', _('اعتماد')),
        ('REJECT', _('رفض')),
        ('CANCEL', _('إلغاء')),
        ('LOGIN', _('تسجيل دخول')),
        ('LOGOUT', _('خروج')),
        ('PASSWORD_CHANGE', _('تغيير كلمة المرور')),
        ('PERMISSION_CHANGE', _('تغيير صلاحيات')),
        ('LOCK_PERIOD', _('إقفال فترة')),
        ('UNLOCK_PERIOD', _('فتح فترة')),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('المستخدم'))
    action = models.CharField(_('العملية'), max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(_('النموذج'), max_length=100)
    object_id = models.PositiveIntegerField(_('رقم الكائن'), null=True, blank=True)
    object_repr = models.CharField(_('وصف الكائن'), max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.CharField(_('الجهاز'), max_length=500, blank=True)
    old_data = models.JSONField(_('البيانات قبل'), default=dict, blank=True)
    new_data = models.JSONField(_('البيانات بعد'), default=dict, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    timestamp = models.DateTimeField(_('التاريخ والوقت'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل عملية')
        verbose_name_plural = _('سجلات العمليات')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.model_name} - {self.timestamp}"
