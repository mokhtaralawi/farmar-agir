"""
Payroll application models - إدارة الرواتب
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Employee(models.Model):
    """الموظفون"""
    STATUS_CHOICES = [
        ('ACTIVE', _('نشط')),
        ('INACTIVE', _('غير نشط')),
        ('ON_LEAVE', _('في إجازة')),
    ]

    code = models.CharField(_('الكود'), max_length=20, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    position = models.CharField(_('المسمى الوظيفي'), max_length=200, blank=True)
    basic_salary = models.DecimalField(_('الراتب الأساسي'), max_digits=12, decimal_places=2)
    allowances = models.DecimalField(_('البدلات'), max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(_('الخصومات'), max_digits=12, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    hire_date = models.DateField(_('تاريخ التعيين'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('موظف')
        verbose_name_plural = _('الموظفون')

    def __str__(self):
        return f"{self.code} - {self.name}"


class Attendance(models.Model):
    """الحضور والغياب"""
    ATTENDANCE_TYPES = [
        ('PRESENT', _('حاضر')),
        ('ABSENT', _('غائب')),
        ('LATE', _('متأخر')),
        ('HALF_DAY', _('نصف يوم')),
        ('ON_LEAVE', _('إجازة')),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('الموظف'))
    date = models.DateField(_('التاريخ'))
    attendance_type = models.CharField(_('الحالة'), max_length=10, choices=ATTENDANCE_TYPES, default='PRESENT')
    check_in = models.TimeField(_('وقت الحضور'), null=True, blank=True)
    check_out = models.TimeField(_('وقت الانصراف'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('حضور')
        verbose_name_plural = _('الحضور والغياب')
        unique_together = ['employee', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date}"


class Leave(models.Model):
    """الإجازات"""
    LEAVE_TYPES = [
        ('ANNUAL', _('سنوية')),
        ('SICK', _('مرضية')),
        ('EMERGENCY', _('طارئة')),
        ('UNPAID', _('بدون راتب')),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('الموظف'))
    leave_type = models.CharField(_('نوع الإجازة'), max_length=10, choices=LEAVE_TYPES)
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name=_('المعتمد'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('إجازة')
        verbose_name_plural = _('الإجازات')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()}"


class SalaryAdvance(models.Model):
    """السلف"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('الموظف'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    date = models.DateField(_('التاريخ'))
    remaining = models.DecimalField(_('المتبقي'), max_digits=12, decimal_places=2)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('سلفة')
        verbose_name_plural = _('السلف')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.amount}"


class Payroll(models.Model):
    """مسير الرواتب"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('APPROVED', _('معتمد')),
        ('PAID', _('مدفوع')),
    ]

    payroll_number = models.CharField(_('رقم المسير'), max_length=50, unique=True)
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))
    total_salary = models.DecimalField(_('إجمالي الرواتب'), max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(_('إجمالي الخصومات'), max_digits=15, decimal_places=2, default=0)
    total_bonuses = models.DecimalField(_('إجمالي الحوافز'), max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(_('الصافي'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='payrolls_created', verbose_name=_('أنشأه'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='payrolls_approved', verbose_name=_('اعتمده'))
    paid_at = models.DateTimeField(_('تاريخ الدفع'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('مسير رواتب')
        verbose_name_plural = _('مسيرات الرواتب')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.payroll_number} - {self.period_start} إلى {self.period_end}"


class PayrollLine(models.Model):
    """سطور مسير الرواتب"""
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='lines',
                                 verbose_name=_('المسير'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('الموظف'))
    basic_salary = models.DecimalField(_('الراتب الأساسي'), max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(_('البدلات'), max_digits=12, decimal_places=2, default=0)
    bonuses = models.DecimalField(_('الحوافز والمكافآت'), max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(_('الخصومات'), max_digits=12, decimal_places=2, default=0)
    advances = models.DecimalField(_('السلف'), max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(_('صافي الراتب'), max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = _('سطر راتب')
        verbose_name_plural = _('سطور الرواتب')

    def save(self, *args, **kwargs):
        self.net_salary = self.basic_salary + self.allowances + self.bonuses - self.deductions - self.advances
        super().save(*args, **kwargs)
