"""
Partners application models - إدارة الرعية والمقاوته
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Farmer(models.Model):
    """الرعويون"""
    STATUS_CHOICES = [
        ('ACTIVE', _('نشط')),
        ('INACTIVE', _('غير نشط')),
        ('SUSPENDED', _('معلق')),
    ]

    code = models.CharField(_('رقم الرعوي'), max_length=20, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=50)
    id_number = models.CharField(_('رقم الهوية'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    city = models.CharField(_('المدينة'), max_length=100, blank=True)
    region = models.CharField(_('المنطقة'), max_length=100, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='ACTIVE')

    # Financial
    current_balance = models.DecimalField(_('الرصيد الحالي'), max_digits=15, decimal_places=2, default=0)
    total_receivables = models.DecimalField(_('إجمالي المستحقات'), max_digits=15, decimal_places=2, default=0)
    total_paid = models.DecimalField(_('إجمالي المدفوع'), max_digits=15, decimal_places=2, default=0)
    total_discounts = models.DecimalField(_('إجمالي الخصومات'), max_digits=15, decimal_places=2, default=0)
    total_commissions = models.DecimalField(_('إجمالي العمولات'), max_digits=15, decimal_places=2, default=0)
    total_expenses = models.DecimalField(_('إجمالي المصروفات'), max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('رعوي')
        verbose_name_plural = _('الرعويون')
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @staticmethod
    def generate_code():
        last_farmer = Farmer.objects.filter(code__startswith='FRM-').order_by('-code').first()
        if last_farmer and last_farmer.code[4:].isdigit():
            next_num = int(last_farmer.code[4:]) + 1
        else:
            next_num = 1
        return f"FRM-{next_num:03d}"


class Buyer(models.Model):
    """المقاوته"""
    STATUS_CHOICES = [
        ('ACTIVE', _('نشط')),
        ('INACTIVE', _('غير نشط')),
        ('SUSPENDED', _('موقوف')),
    ]

    code = models.CharField(_('رقم العميل'), max_length=20, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=50)
    address = models.TextField(_('العنوان'), blank=True)
    city = models.CharField(_('المدينة'), max_length=100, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    credit_limit = models.DecimalField(_('الحد الائتماني'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='ACTIVE')

    # Financial
    current_balance = models.DecimalField(_('الرصيد الحالي'), max_digits=15, decimal_places=2, default=0)
    total_purchases = models.DecimalField(_('إجمالي المشتريات'), max_digits=15, decimal_places=2, default=0)
    total_paid = models.DecimalField(_('إجمالي المسدد'), max_digits=15, decimal_places=2, default=0)
    total_remaining = models.DecimalField(_('إجمالي المتبقي'), max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مقوت')
        verbose_name_plural = _('المقاوته')
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @staticmethod
    def generate_code():
        last_buyer = Buyer.objects.filter(code__startswith='BYR-').order_by('-code').first()
        if last_buyer and last_buyer.code[4:].isdigit():
            next_num = int(last_buyer.code[4:]) + 1
        else:
            next_num = 1
        return f"BYR-{next_num:03d}"


class Discount(models.Model):
    """الخصومات"""
    DISCOUNT_TYPES = [
        ('FIXED_AMOUNT', _('مبلغ ثابت')),
        ('PERCENTAGE', _('نسبة')),
        ('TEMPORARY', _('مؤقت')),
        ('PERMANENT', _('دائم')),
    ]
    TARGET_TYPES = [
        ('FARMER', _('رعوي')),
        ('BUYER', _('مقوت')),
        ('INVOICE', _('فاتورة')),
        ('ALL', _('جميع الفواتير')),
    ]

    name = models.CharField(_('الاسم'), max_length=200)
    discount_type = models.CharField(_('نوع الخصم'), max_length=20, choices=DISCOUNT_TYPES)
    target_type = models.CharField(_('نوع المستهدف'), max_length=20, choices=TARGET_TYPES)
    value = models.DecimalField(_('القيمة'), max_digits=10, decimal_places=2)
    target_farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=_('الرعوي المستهدف'))
    target_buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, null=True, blank=True,
                                      verbose_name=_('الرعوي المستهدف'))
    start_date = models.DateField(_('تاريخ البداية'), null=True, blank=True)
    end_date = models.DateField(_('تاريخ النهاية'), null=True, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('خصم')
        verbose_name_plural = _('الخصومات')

    def __str__(self):
        return self.name
