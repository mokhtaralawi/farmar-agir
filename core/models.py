"""
Core application models - الإعدادات العامة ودليل الحسابات
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Branch(models.Model):
    """الفروع"""
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('فرع')
        verbose_name_plural = _('الفروع')

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """المخازن"""
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('الفرع'))
    is_default = models.BooleanField(_('المخزن الافتراضي'), default=False)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('مخزن')
        verbose_name_plural = _('المخازن')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            Warehouse.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Currency(models.Model):
    """العملات"""
    code = models.CharField(_('الكود'), max_length=10, unique=True)
    name = models.CharField(_('الاسم'), max_length=100)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    symbol = models.CharField(_('الرمز'), max_length=10)
    is_default = models.BooleanField(_('العملة الافتراضية'), default=False)
    exchange_rate = models.DecimalField(_('سعر الصرف'), max_digits=12, decimal_places=4, default=1.0000)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('عملة')
        verbose_name_plural = _('العملات')

    def __str__(self):
        return f"{self.code} - {self.symbol}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Currency.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class AccountType(models.Model):
    """أنواع الحسابات - دليل الحسابات الهرمي"""
    ACCOUNT_TYPES = [
        ('ASSETS', _('الأصول')),
        ('LIABILITIES', _('الخصوم')),
        ('EQUITY', _('حقوق الملكية')),
        ('REVENUE', _('الإيرادات')),
        ('EXPENSES', _('المصروفات')),
    ]

    code = models.CharField(_('الكود'), max_length=50, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    account_type = models.CharField(_('نوع الحساب'), max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='children', verbose_name=_('الحساب الأب'))
    level = models.PositiveIntegerField(_('المستوى'), default=1)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('نوع حساب')
        verbose_name_plural = _('أنواع الحسابات')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
        super().save(*args, **kwargs)


class Account(models.Model):
    """الحسابات - دليل الحسابات الفعلي"""
    code = models.CharField(_('الكود'), max_length=50, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE, verbose_name=_('نوع الحساب'))
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='child_accounts', verbose_name=_('الحساب الأب'))
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('العملة'))
    balance = models.DecimalField(_('الرصيد'), max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('حساب')
        verbose_name_plural = _('الحسابات')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class SystemSettings(models.Model):
    """إعدادات النظام العامة"""
    company_name = models.CharField(_('اسم المؤسسة'), max_length=300, default='الوساطة الزراعية')
    company_name_en = models.CharField(_('اسم المؤسسة بالإنجليزية'), max_length=300, default='Agri Bridge')
    logo = models.ImageField(_('الشعار'), upload_to='settings/', blank=True, null=True)
    address = models.TextField(_('العنوان'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('العملة الافتراضية'))
    default_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('الفرع الافتراضي'))
    default_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True,
                                           verbose_name=_('المخزن الافتراضي'))
    commission_percentage = models.DecimalField(_('نسبة العمولة الافتراضية'), max_digits=5, decimal_places=2,
                                               default=5.00)
    tax_enabled = models.BooleanField(_('تفعيل الضرائب'), default=False)
    tax_percentage = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2,
                                        default=15.00)
    print_thermal_58 = models.BooleanField(_('طباعة حرارية 58mm'), default=True)
    print_thermal_80 = models.BooleanField(_('طباعة حرارية 80mm'), default=False)
    print_a4 = models.BooleanField(_('طباعة A4'), default=False)
    invoice_copies = models.PositiveIntegerField(_('عدد نسخ الفاتورة'), default=2)
    default_language = models.CharField(_('اللغة الافتراضية'), max_length=5, choices=[('ar', 'العربية'), ('en', 'English')], default='ar')
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إعدادات النظام')
        verbose_name_plural = _('إعدادات النظام')

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        if not self.pk and not SystemSettings.objects.exists():
            super().save(*args, **kwargs)
        elif SystemSettings.objects.exists():
            settings = SystemSettings.objects.first()
            settings.__dict__.update(self.__dict__)
            settings.save()
        else:
            super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        return cls.objects.first() or cls.objects.create()


class PeriodLock(models.Model):
    """إقفال الفترات المالية"""
    PERIOD_TYPES = [
        ('DAILY', _('يومي')),
        ('MONTHLY', _('شهري')),
        ('YEARLY', _('سنوي')),
    ]

    period_type = models.CharField(_('نوع الفترة'), max_length=10, choices=PERIOD_TYPES)
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    is_locked = models.BooleanField(_('مقفل'), default=False)
    locked_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('المستخدم'))
    locked_at = models.DateTimeField(_('تاريخ الإقفال'), auto_now_add=True)
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('إقفال فترة')
        verbose_name_plural = _('إقفال الفترات')
        unique_together = ['period_type', 'start_date', 'end_date']

    def __str__(self):
        return f"{self.get_period_type_display()} - {self.start_date} إلى {self.end_date}"


class CommissionRule(models.Model):
    """قواعد احتساب العمولة"""
    TYPE_CHOICES = [
        ('FIXED_PERCENT', _('نسبة ثابتة')),
        ('FARMER_SPECIFIC', _('نسبة حسب الرعوي')),
        ('PRODUCT_SPECIFIC', _('نسبة حسب الصنف')),
        ('SEASONAL', _('نسبة حسب الموسم')),
        ('FIXED_AMOUNT', _('مبلغ ثابت')),
        ('FORMULA', _('معادلة مخصصة')),
    ]

    name = models.CharField(_('الاسم'), max_length=200)
    rule_type = models.CharField(_('نوع القاعدة'), max_length=20, choices=TYPE_CHOICES)
    value = models.DecimalField(_('القيمة'), max_digits=10, decimal_places=2, null=True, blank=True)
    formula = models.TextField(_('المعادلة'), blank=True, help_text='مثال: price * 0.05 + 10')
    farmer = models.ForeignKey('partners.Farmer', on_delete=models.CASCADE, null=True, blank=True,
                                verbose_name=_('الرعوي'))
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True,
                                 verbose_name=_('الصنف'))
    season_start = models.DateField(_('بداية الموسم'), null=True, blank=True)
    season_end = models.DateField(_('نهاية الموسم'), null=True, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    priority = models.PositiveIntegerField(_('الأولوية'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('قاعدة عمولة')
        verbose_name_plural = _('قواعد العمولة')

    def __str__(self):
        return self.name


# ---- Common models used by multiple apps ----

class PaymentMethod(models.Model):
    """طرق الدفع"""
    code = models.CharField(_('الكود'), max_length=20, unique=True)
    name = models.CharField(_('الاسم'), max_length=100)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('طريقة دفع')
        verbose_name_plural = _('طرق الدفع')

    def __str__(self):
        return self.name


class Bank(models.Model):
    """الحسابات البنكية"""
    name = models.CharField(_('اسم البنك'), max_length=200)
    account_number = models.CharField(_('رقم الحساب'), max_length=50, unique=True)
    iban = models.CharField(_('الآيبان'), max_length=50, blank=True)
    branch_name = models.CharField(_('اسم الفرع'), max_length=200, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('العملة'))
    balance = models.DecimalField(_('الرصيد'), max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('حساب بنكي')
        verbose_name_plural = _('الحسابات البنكية')

    def __str__(self):
        return f"{self.name} - {self.account_number}"


class ActivityLog(models.Model):
    """سجل النشاطات"""
    ACTION_CHOICES = [
        ('LOGIN', _('تسجيل دخول')),
        ('LOGOUT', _('تسجيل خروج')),
        ('SALES_CREATE', _('إنشاء فاتورة بيع')),
        ('SALES_EDIT', _('تعديل فاتورة بيع')),
        ('RECEIVING_CREATE', _('إنشاء فاتورة استلام')),
        ('RECEIVING_EDIT', _('تعديل فاتورة استلام')),
        ('COLLECTION_CREATE', _('إنشاء سند قبض')),
        ('PAYMENT_CREATE', _('إنشاء سند صرف')),
        ('SETTLEMENT_CREATE', _('إنشاء تسوية')),
        ('PRODUCT_CREATE', _('إضافة صنف')),
        ('PARTNER_CREATE', _('إضافة شريك')),
        ('INVENTORY_ADJUST', _('تعديل مخزون')),
        ('EXPENSE_CREATE', _('تسجيل مصروف')),
        ('SETTINGS_CHANGE', _('تعديل إعدادات')),
        ('USER_CREATE', _('إضافة مستخدم')),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('المستخدم'))
    action = models.CharField(_('العملية'), max_length=30, choices=ACTION_CHOICES)
    description = models.TextField(_('الوصف'))
    reference_type = models.CharField(_('نوع المرجع'), max_length=50, blank=True)
    reference_id = models.PositiveIntegerField(_('رقم المرجع'), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    created_at = models.DateTimeField(_('التاريخ'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل نشاط')
        verbose_name_plural = _('سجل النشاطات')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.user} - {self.created_at}"
