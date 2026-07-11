"""
Payments application models - صرف مستحقات الرعية
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentVoucher(models.Model):
    """سند الصرف"""
    PAYMENT_METHODS = [
        ('CASH', _('نقدي')),
        ('BANK_TRANSFER', _('تحويل بنكي')),
        ('CHECK', _('شيك')),
        ('OTHER', _('أخرى')),
    ]

    voucher_number = models.CharField(_('رقم السند'), max_length=50, unique=True)
    farmer = models.ForeignKey('partners.Farmer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHODS, default='CASH')
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2)
    bank = models.ForeignKey('core.Bank', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الحساب البنكي'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    date = models.DateField(_('التاريخ'))
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('سند صرف')
        verbose_name_plural = _('سندات الصرف')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.voucher_number} - {self.farmer} - {self.amount}"


class FarmerSettlement(models.Model):
    """التسوية مع الرعية"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('PENDING', _('بانتظار الاعتماد')),
        ('APPROVED', _('معتمد')),
    ]

    settlement_number = models.CharField(_('رقم التسوية'), max_length=50, unique=True)
    farmer = models.ForeignKey('partners.Farmer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))
    total_sales = models.DecimalField(_('إجمالي المبيعات'), max_digits=15, decimal_places=2, default=0)
    total_commissions = models.DecimalField(_('إجمالي العمولات'), max_digits=15, decimal_places=2, default=0)
    total_discounts = models.DecimalField(_('إجمالي الخصومات'), max_digits=15, decimal_places=2, default=0)
    total_expenses = models.DecimalField(_('إجمالي المصروفات'), max_digits=15, decimal_places=2, default=0)
    total_paid = models.DecimalField(_('إجمالي المدفوعات'), max_digits=15, decimal_places=2, default=0)
    net_payable = models.DecimalField(_('صافي المستحق'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='settlements_created', verbose_name=_('أنشأه'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='settlements_approved', verbose_name=_('اعتمده'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('تسوية رعوي')
        verbose_name_plural = _('تسويات الرعية')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.settlement_number} - {self.farmer}"


class DailySettlement(models.Model):
    """التسوية اليومية للرعوي"""
    farmer = models.ForeignKey('partners.Farmer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    date = models.DateField(_('التاريخ'))
    received_value = models.DecimalField(_('قيمة المستلم'), max_digits=15, decimal_places=2, default=0)
    sold_value = models.DecimalField(_('قيمة المباع'), max_digits=15, decimal_places=2, default=0)
    commission = models.DecimalField(_('العمولة'), max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(_('الخصم'), max_digits=15, decimal_places=2, default=0)
    expense = models.DecimalField(_('المصروف'), max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(_('الصافي'), max_digits=15, decimal_places=2, default=0)
    is_settled = models.BooleanField(_('تم التسوية'), default=False)
    settlement = models.ForeignKey(FarmerSettlement, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('التسوية'))

    class Meta:
        verbose_name = _('تسوية يومية')
        verbose_name_plural = _('التسويات اليومية')
        unique_together = ['farmer', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.farmer} - {self.date}"
