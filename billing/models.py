"""
Billing application models - بيع المنتجات للباعة
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class SalesInvoice(models.Model):
    """فاتورة البيع"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('PENDING', _('بانتظار الاعتماد')),
        ('APPROVED', _('معتمد')),
        ('CANCELLED', _('ملغي')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    buyer = models.ForeignKey('partners.Buyer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    warehouse = models.ForeignKey('core.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('المخزن'))
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    date = models.DateField(_('التاريخ'))
    time = models.TimeField(_('الوقت'), auto_now_add=True)
    total_amount = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    total_discount = models.DecimalField(_('إجمالي الخصم'), max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(_('خصم الفاتورة'), max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(_('الصافي'), max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='sales_invoices', verbose_name=_('أنشأه'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='approved_sales', verbose_name=_('اعتمده'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('فاتورة بيع')
        verbose_name_plural = _('فواتير البيع')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.buyer}"

    def recalculate_total(self):
        self.total_amount = sum(item.total for item in self.items.all())
        self.net_amount = self.total_amount - self.total_discount
        self.save()


class SalesItem(models.Model):
    """أصناف فاتورة البيع"""
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items',
                                 verbose_name=_('الفاتورة'))
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    unit = models.ForeignKey('products.Unit', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الوحدة'))
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=12, decimal_places=2)
    discount = models.DecimalField(_('الخصم'), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('صنف بيع')
        verbose_name_plural = _('أصناف البيع')

    def __str__(self):
        return f"{self.product} - {self.quantity} {self.unit}"

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price) - self.discount
        super().save(*args, **kwargs)


class SalesReturn(models.Model):
    """مرتجع البيع"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('APPROVED', _('معتمد')),
        ('CANCELLED', _('ملغي')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE,
                                       verbose_name=_('فاتورة البيع الأصلية'))
    buyer = models.ForeignKey('partners.Buyer', on_delete=models.CASCADE, verbose_name=_('الرعوي'))
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    date = models.DateField(_('التاريخ'))
    total_amount = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('مرتجع بيع')
        verbose_name_plural = _('مرتجعات البيع')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.buyer}"


class SalesReturnItem(models.Model):
    """أصناف مرتجع البيع"""
    return_invoice = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items',
                                        verbose_name=_('الفاتورة'))
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=12, decimal_places=2)
    total = models.DecimalField(_('الإجمالي'), max_digits=15, decimal_places=2, default=0)
    reason = models.TextField(_('السبب'), blank=True)

    class Meta:
        verbose_name = _('صنف مرتجع بيع')
        verbose_name_plural = _('أصناف مرتجع البيع')

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
