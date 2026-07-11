"""
Accounts application models - إدارة المستخدمين والأدوار والصلاحيات
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """الأدوار"""
    name = models.CharField(_('الاسم'), max_length=100, unique=True)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    description = models.TextField(_('الوصف'), blank=True)
    is_system = models.BooleanField(_('دور نظامي'), default=False)
    permissions = models.JSONField(_('الصلاحيات'), default=dict, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('دور')
        verbose_name_plural = _('الأدوار')

    def __str__(self):
        return self.name


class User(AbstractUser):
    """المستخدمون"""
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('اسم المستخدم'),
        max_length=150,
        unique=True,
        help_text=_('مطلوب. 150 حرف أو أقل. حروف وأرقام و @/./+/-/_ فقط.'),
        validators=[username_validator],
        error_messages={'unique': _("اسم المستخدم موجود مسبقاً.")},
    )
    full_name = models.CharField(_('الاسم الكامل'), max_length=250, blank=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=50, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    avatar = models.ImageField(_('الصورة الشخصية'), upload_to='users/avatars/', blank=True, null=True)
    roles = models.ManyToManyField(Role, verbose_name=_('الأدوار'), blank=True)
    assigned_branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('الفرع'))
    is_locked = models.BooleanField(_('مقفل'), default=False)
    login_attempts = models.PositiveIntegerField(_('محاولات الدخول'), default=0)
    last_login_ip = models.GenericIPAddressField(_('آخر IP'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    webauthn_credential_id = models.TextField(_('معرف البصمة'), blank=True, null=True)
    webauthn_public_key = models.TextField(_('مفتاح البصمة'), blank=True, null=True)
    webauthn_enabled = models.BooleanField(_('تفعيل البصمة'), default=False)

    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمون')

    def __str__(self):
        return self.full_name or self.username

    def has_permission(self, app_name, action):
        for role in self.roles.filter(is_active=True):
            perms = role.permissions
            if app_name in perms and action in perms[app_name] and perms[app_name][action]:
                return True
        if self.is_staff or self.is_superuser:
            return True
        return False

    def get_merged_permissions(self):
        merged = {}
        for role in self.roles.filter(is_active=True):
            for app, actions in role.permissions.items():
                if app not in merged:
                    merged[app] = {}
                for action, value in actions.items():
                    merged[app][action] = merged[app].get(action, False) or value
        return merged


class Notification(models.Model):
    """الإشعارات"""
    NOTIFICATION_TYPES = [
        ('STOCK_LOW', _('انخفاض المخزون')),
        ('DEBT_ALERT', _('تنبيه ديون')),
        ('SETTLEMENT_DUE', _('تسوية مستحقة')),
        ('APPROVAL_PENDING', _('بانتظار الاعتماد')),
        ('ERROR', _('خطأ')),
        ('PERIOD_END', _('انتهاء فترة مالية')),
        ('GENERAL', _('عام')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    title = models.CharField(_('العنوان'), max_length=300)
    message = models.TextField(_('الرسالة'))
    notification_type = models.CharField(_('نوع الإشعار'), max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(_('مقروء'), default=False)
    link = models.URLField(_('الرابط'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('إشعار')
        verbose_name_plural = _('الإشعارات')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user}"
