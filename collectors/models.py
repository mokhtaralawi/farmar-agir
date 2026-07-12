"""
Collectors application models - التحصيل من المقاوته
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class CollectionReceipt(models.Model):
    """سند القبض"""
    PAYMENT_METHODS = [
        ('CASH', _('نقدي')),
        ('BANK_TRANSFER', _('تحويل بنكي')),
        ('CHECK', _('شيك')),
        ('OTHER', _('أخرى')),
    ]

    receipt_number = models.CharField(_('رقم السند'), max_length=50, unique=True)
    buyer = models.ForeignKey('partners.Buyer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHODS, default='CASH')
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2)
    discount = models.DecimalField(_('الخصم'), max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(_('الصافي'), max_digits=15, decimal_places=2, default=0)
    bank = models.ForeignKey('core.Bank', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الحساب البنكي'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    date = models.DateField(_('التاريخ'))
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('سند قبض')
        verbose_name_plural = _('سندات القبض')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.receipt_number} - {self.buyer} - {self.amount}"
