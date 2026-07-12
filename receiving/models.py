"""
Receiving application models - استلام المنتجات من الرعية
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class ReceivingInvoice(models.Model):
    """فاتورة الاستلام"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('PENDING', _('بانتظار الاعتماد')),
        ('APPROVED', _('معتمد')),
        ('CANCELLED', _('ملغي')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    farmer = models.ForeignKey('partners.Farmer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    warehouse = models.ForeignKey('core.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('المخزن'))
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    date = models.DateField(_('التاريخ'))
    time = models.TimeField(_('الوقت'), auto_now_add=True)
    total_amount = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(_('الخصم'), max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(_('الصافي'), max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='receiving_invoices', verbose_name=_('أنشأه'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='approved_receiving', verbose_name=_('اعتمده'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('فاتورة استلام')
        verbose_name_plural = _('فواتير الاستلام')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.farmer}"

    def recalculate_total(self):
        self.total_amount = sum(item.total for item in self.items.all())
        self.save()


class ReceivingItem(models.Model):
    """أصناف فاتورة الاستلام"""
    invoice = models.ForeignKey(ReceivingInvoice, on_delete=models.CASCADE, related_name='items',
                                 verbose_name=_('الفاتورة'))
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    unit = models.ForeignKey('products.Unit', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الوحدة'))
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=12, decimal_places=2)
    total = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    quality_grade = models.ForeignKey('products.QualityGrade', on_delete=models.SET_NULL, null=True,
                                       blank=True, verbose_name=_('درجة الجودة'))
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('صنف استلام')
        verbose_name_plural = _('أصناف الاستلام')

    def __str__(self):
        return f"{self.product} - {self.quantity} {self.unit}"

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class ReturnInvoice(models.Model):
    """مرتجع الاستلام"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('APPROVED', _('معتمد')),
        ('CANCELLED', _('ملغي')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    receiving_invoice = models.ForeignKey(ReceivingInvoice, on_delete=models.CASCADE,
                                           verbose_name=_('فاتورة الاستلام الأصلية'))
    farmer = models.ForeignKey('partners.Farmer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    date = models.DateField(_('التاريخ'))
    total_amount = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('مرتجع استلام')
        verbose_name_plural = _('مرتجعات الاستلام')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.farmer}"


class ReturnItem(models.Model):
    """أصناف مرتجع الاستلام"""
    return_invoice = models.ForeignKey(ReturnInvoice, on_delete=models.CASCADE, related_name='items',
                                        verbose_name=_('الفاتورة'))
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=12, decimal_places=2)
    total = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    reason = models.TextField(_('السبب'), blank=True)

    class Meta:
        verbose_name = _('صنف مرتجع')
        verbose_name_plural = _('أصناف المرتجع')

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
