"""
Expenses application models - إدارة المصروفات
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ExpenseCategory(models.Model):
    """تصنيفات المصروفات"""
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    account = models.ForeignKey('core.Account', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_('الحساب المحاسبي'))
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('تصنيف مصروفات')
        verbose_name_plural = _('تصنيفات المصروفات')

    def __str__(self):
        return self.name


class Expense(models.Model):
    """المصروفات"""
    PAYMENT_METHODS = [
        ('CASH', _('نقدي')),
        ('BANK_TRANSFER', _('تحويل بنكي')),
        ('CHECK', _('شيك')),
        ('OTHER', _('أخرى')),
    ]

    voucher_number = models.CharField(_('رقم السند'), max_length=50, unique=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name=_('التصنيف'))
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2)
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHODS, default='CASH')
    cashbox = models.ForeignKey('cashbox.CashBox', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_('الصندوق'))
    bank = models.ForeignKey('core.Bank', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الحساب البنكي'))
    beneficiary = models.CharField(_('المستفيد'), max_length=300, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    attachment = models.FileField(_('المرفق'), upload_to='expenses/attachments/', blank=True, null=True)
    date = models.DateField(_('التاريخ'))
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('مصروف')
        verbose_name_plural = _('المصروفات')
        ordering = ['-date']

    def __str__(self):
        return f"{self.voucher_number} - {self.category} - {self.amount}"
