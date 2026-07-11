"""
Products application models - إدارة الأصناف والفئات والوحدات
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Unit(models.Model):
    """الوحدات القياسية"""
    code = models.CharField(_('الكود'), max_length=20, unique=True)
    name = models.CharField(_('الاسم'), max_length=100)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    conversion_factor = models.DecimalField(_('عامل التحويل'), max_digits=10, decimal_places=4, default=1.0000)
    base_unit = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='derived_units', verbose_name=_('الوحدة الأساسية'))
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('وحدة')
        verbose_name_plural = _('الوحدات')

    def __str__(self):
        return self.name


class Category(models.Model):
    """فئات المنتجات"""
    name = models.CharField(_('الاسم'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='children', verbose_name=_('الفئة الأب'))
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('فئة')
        verbose_name_plural = _('الفئات')
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """الأصناف"""
    STATUS_CHOICES = [
        ('ACTIVE', _('نشط')),
        ('INACTIVE', _('معطل')),
        ('OUT_OF_STOCK', _('نفذ من المخزون')),
    ]

    code = models.CharField(_('الكود'), max_length=50, unique=True)
    name = models.CharField(_('الاسم'), max_length=300)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=300, blank=True)
    barcode = models.CharField(_('الباركود'), max_length=100, blank=True, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('الفئة'))
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_('الوحدة'))
    description = models.TextField(_('الوصف'), blank=True)
    image = models.ImageField(_('الصورة'), upload_to='products/photos/', blank=True, null=True)
    status = models.CharField(_('الحالة'), max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    min_stock = models.DecimalField(_('الحد الأدنى للمخزون'), max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('صنف')
        verbose_name_plural = _('الأصناف')
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @staticmethod
    def generate_code():
        last = Product.objects.filter(code__startswith='PRD-').order_by('-code').first()
        if last and len(last.code) > 4 and last.code[4:].isdigit():
            next_num = int(last.code[4:]) + 1
        else:
            next_num = 1
        return f"PRD-{next_num:03d}"


class QualityGrade(models.Model):
    """درجات الجودة"""
    name = models.CharField(_('الاسم'), max_length=100)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    priority = models.PositiveIntegerField(_('الأولوية'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('درجة جودة')
        verbose_name_plural = _('درجات الجودة')

    def __str__(self):
        return self.name


class ProductPrice(models.Model):
    """أسعار المنتجات"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('الصنف'))
    buy_price = models.DecimalField(_('سعر الشراء'), max_digits=12, decimal_places=2, default=0)
    sell_price = models.DecimalField(_('سعر البيع'), max_digits=12, decimal_places=2, default=0)
    min_price = models.DecimalField(_('أقل سعر'), max_digits=12, decimal_places=2, default=0)
    max_price = models.DecimalField(_('أعلى سعر'), max_digits=12, decimal_places=2, default=0)
    date = models.DateField(_('التاريخ'), auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('المستخدم'))

    class Meta:
        verbose_name = _('سعر المنتج')
        verbose_name_plural = _('أسعار المنتجات')
        ordering = ['-date']

    def __str__(self):
        return f"{self.product} - {self.sell_price}"
