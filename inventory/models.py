"""
Inventory application models - إدارة المخزون
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class InventoryItem(models.Model):
    """المخزون اللحظي"""
    MOVEMENT_TYPES = [
        ('RECEIVED', _('مستلم')),
        ('SOLD', _('مباع')),
        ('RETURNED', _('مرتجع')),
        ('DAMAGED', _('تالف')),
        ('WASTED', _('هالك')),
        ('RESERVED', _('محجوز')),
        ('LOST', _('مفقود')),
        ('STOLEN', _('مسروق')),
    ]

    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    warehouse = models.ForeignKey('core.Warehouse', on_delete=models.CASCADE, verbose_name=_('المخزن'))

    received_qty = models.DecimalField(_('الكمية المستلمة'), max_digits=12, decimal_places=2, default=0)
    sold_qty = models.DecimalField(_('الكمية المباعة'), max_digits=12, decimal_places=2, default=0)
    remaining_qty = models.DecimalField(_('الكمية المتبقية'), max_digits=12, decimal_places=2, default=0)
    returned_qty = models.DecimalField(_('الكمية المرتجعة'), max_digits=12, decimal_places=2, default=0)
    damaged_qty = models.DecimalField(_('الكمية التالفة'), max_digits=12, decimal_places=2, default=0)
    reserved_qty = models.DecimalField(_('الكمية المحجوزة'), max_digits=12, decimal_places=2, default=0)

    avg_price = models.DecimalField(_('المتوسط السعري'), max_digits=12, decimal_places=2, default=0)
    last_buy_price = models.DecimalField(_('آخر سعر شراء'), max_digits=12, decimal_places=2, default=0)
    last_sell_price = models.DecimalField(_('آخر سعر بيع'), max_digits=12, decimal_places=2, default=0)

    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مخزون صنف')
        verbose_name_plural = _('المخزون')
        unique_together = ['product', 'warehouse']

    def __str__(self):
        return f"{self.product} - {self.warehouse} - {self.remaining_qty}"

    @property
    def available_qty(self):
        return self.remaining_qty - self.reserved_qty


class InventoryMovement(models.Model):
    """حركات المخزون"""
    MOVEMENT_TYPES = [
        ('RECEIVED', _('استلام')),
        ('SOLD', _('بيع')),
        ('RETURN_IN', _('مرتجع إلى الرعوي')),
        ('RETURN_OUT', _('مرتجع من المقوت')),
        ('DAMAGED', _('تالف')),
        ('WASTED', _('هالك')),
        ('LOST', _('مفقود')),
        ('STOLEN', _('مسروق')),
        ('TRANSFER_IN', _('تحويل وارد')),
        ('TRANSFER_OUT', _('تحويل صادر')),
    ]

    movement_type = models.CharField(_('نوع الحركة'), max_length=20, choices=MOVEMENT_TYPES)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    warehouse = models.ForeignKey('core.Warehouse', on_delete=models.CASCADE, verbose_name=_('المخزن'))
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=2)
    price = models.DecimalField(_('السعر'), max_digits=12, decimal_places=2, default=0)
    unit = models.ForeignKey('products.Unit', on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الوحدة'))
    reference_type = models.CharField(_('نوع المرجع'), max_length=50, blank=True)
    reference_id = models.PositiveIntegerField(_('رقم المرجع'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    reason = models.TextField(_('السبب'), blank=True)
    responsible = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name=_('المسؤول'))
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='inventory_movements', verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('حركة مخزون')
        verbose_name_plural = _('حركات المخزون')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product} - {self.quantity}"


class InventoryAdjustment(models.Model):
    """تسويات المخزون"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name=_('الصنف'))
    warehouse = models.ForeignKey('core.Warehouse', on_delete=models.CASCADE, verbose_name=_('المخزن'))
    adjustment_qty = models.DecimalField(_('كمية التسوية'), max_digits=12, decimal_places=2)
    reason = models.TextField(_('السبب'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name=_('المعتمد'))
    is_approved = models.BooleanField(_('معتمد'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تسوية مخزون')
        verbose_name_plural = _('تسويات المخزون')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product} - {self.adjustment_qty}"
