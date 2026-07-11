"""
Cashbox application models - إدارة الصناديق
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class CashBox(models.Model):
    """الصناديق"""
    STATUS_CHOICES = [
        ('OPEN', _('مفتوح')),
        ('CLOSED', _('مغلق')),
        ('SUSPENDED', _('معلق')),
    ]

    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.CASCADE, null=True, blank=True,
                                verbose_name=_('الفرع'))
    opening_balance = models.DecimalField(_('الرصيد الافتتاحي'), max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(_('الرصيد الحالي'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='OPEN')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('صندوق')
        verbose_name_plural = _('الصناديق')

    def __str__(self):
        return f"{self.name} - {self.current_balance}"


class CashTransaction(models.Model):
    """حركات الصندوق"""
    TRANSACTION_TYPES = [
        ('INCOME', _('وارد')),
        ('EXPENSE', _('صادر')),
        ('OPENING', _('رصيد افتتاحي')),
        ('CLOSING', _('رصيد إقفالي')),
        ('TRANSFER_IN', _('تحويل وارد')),
        ('TRANSFER_OUT', _('تحويل صادر')),
    ]

    cashbox = models.ForeignKey(CashBox, on_delete=models.CASCADE, verbose_name=_('الصندوق'))
    transaction_type = models.CharField(_('نوع الحركة'), max_length=15, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2)
    description = models.TextField(_('الوصف'))
    reference_type = models.CharField(_('نوع المرجع'), max_length=50, blank=True)
    reference_id = models.PositiveIntegerField(_('رقم المرجع'), null=True, blank=True)
    balance_before = models.DecimalField(_('الرصيد قبل'), max_digits=15, decimal_places=2, default=0)
    balance_after = models.DecimalField(_('الرصيد بعد'), max_digits=15, decimal_places=2, default=0)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('حركة صندوق')
        verbose_name_plural = _('حركات الصناديق')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cashbox} - {self.get_transaction_type_display()} - {self.amount}"


class DailyCashClosing(models.Model):
    """إقفال الصندوق اليومي"""
    cashbox = models.ForeignKey(CashBox, on_delete=models.CASCADE, verbose_name=_('الصندوق'))
    date = models.DateField(_('التاريخ'))
    opening_balance = models.DecimalField(_('الرصيد الافتتاحي'), max_digits=15, decimal_places=2, default=0)
    total_income = models.DecimalField(_('إجمالي الوارد'), max_digits=15, decimal_places=2, default=0)
    total_expense = models.DecimalField(_('إجمالي الصادر'), max_digits=15, decimal_places=2, default=0)
    closing_balance = models.DecimalField(_('الرصيد الإقفالي'), max_digits=15, decimal_places=2, default=0)
    expected_balance = models.DecimalField(_('الرصيد المتوقع'), max_digits=15, decimal_places=2, default=0)
    difference = models.DecimalField(_('الفرق'), max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('إقفال يومي')
        verbose_name_plural = _('الإقفالات اليومية')
        unique_together = ['cashbox', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.cashbox} - {self.date}"
