"""
Accounting application models - النظام المحاسبي المزدوج
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class JournalEntry(models.Model):
    """القيود اليومية"""
    STATUS_CHOICES = [
        ('DRAFT', _('مسودة')),
        ('PENDING', _('بانتظار الاعتماد')),
        ('APPROVED', _('معتمد')),
        ('POSTED', _('مرحل')),
        ('CANCELLED', _('ملغي')),
    ]

    entry_number = models.CharField(_('رقم القيد'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    time = models.TimeField(_('الوقت'), auto_now_add=True)
    description = models.TextField(_('الوصف'))
    total_debit = models.DecimalField(_('إجمالي المدين'), max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(_('إجمالي الدائن'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    reference_type = models.CharField(_('نوع المرجع'), max_length=50, blank=True)
    reference_id = models.PositiveIntegerField(_('رقم المرجع'), null=True, blank=True)
    attachment = models.FileField(_('المرفق'), upload_to='accounting/attachments/', blank=True, null=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='journal_entries', verbose_name=_('أنشأه'))
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='approved_entries', verbose_name=_('اعتمده'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    is_deleted = models.BooleanField(_('محذوف'), default=False)

    class Meta:
        verbose_name = _('قيد يومي')
        verbose_name_plural = _('القيود اليومية')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_number} - {self.date}"

    def recalculate_totals(self):
        self.total_debit = sum(line.debit for line in self.lines.all())
        self.total_credit = sum(line.credit for line in self.lines.all())
        self.save()

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalEntryLine(models.Model):
    """سطور القيد"""
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines',
                               verbose_name=_('القيد'))
    account = models.ForeignKey('core.Account', on_delete=models.CASCADE, verbose_name=_('الحساب'))
    description = models.CharField(_('الوصف'), max_length=300, blank=True)
    debit = models.DecimalField(_('المدين'), max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(_('الدائن'), max_digits=15, decimal_places=2, default=0)
    partner = models.ForeignKey('partners.Farmer', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_('الرعوي'))
    partner_type = models.CharField(_('نوع الشريك'), max_length=10, null=True, blank=True,
                                     choices=[('FARMER', _('مزارع')), ('BUYER', _('بائع'))])
    partner_obj_id = models.PositiveIntegerField(_('رقم الشريك'), null=True, blank=True)
    currency = models.ForeignKey('core.Currency', on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('العملة'))

    class Meta:
        verbose_name = _('سطر قيد')
        verbose_name_plural = _('سطور القيود')

    def __str__(self):
        return f"{self.account} - {self.debit if self.debit > 0 else self.credit}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.debit > 0 and self.credit > 0:
            raise ValidationError(_('لا يمكن أن يكون السطر مديناً ودائناً في نفس الوقت'))
        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_('يجب أن يكون للسطر قيمة مدينة أو دائنة'))


class LedgerEntry(models.Model):
    """دفتر الأستاذ"""
    account = models.ForeignKey('core.Account', on_delete=models.CASCADE, verbose_name=_('الحساب'))
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, verbose_name=_('القيد'))
    journal_line = models.ForeignKey(JournalEntryLine, on_delete=models.CASCADE, verbose_name=_('سطر القيد'))
    date = models.DateField(_('التاريخ'))
    description = models.CharField(_('الوصف'), max_length=300)
    debit = models.DecimalField(_('المدين'), max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(_('الدائن'), max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(_('الرصيد'), max_digits=15, decimal_places=2, default=0)
    balance_type = models.CharField(_('نوع الرصيد'), max_length=10, choices=[('DEBIT', _('مدين')), ('CREDIT', _('دائن'))], default='DEBIT')

    class Meta:
        verbose_name = _('سجل أستاذ')
        verbose_name_plural = _('سجلات الأستاذ')
        ordering = ['date', 'id']

    def __str__(self):
        return f"{self.account} - {self.date} - {self.balance}"


class TrialBalance(models.Model):
    """ميزان المراجعة"""
    date = models.DateField(_('التاريخ'))
    account = models.ForeignKey('core.Account', on_delete=models.CASCADE, verbose_name=_('الحساب'))
    opening_balance = models.DecimalField(_('الرصيد الافتتاحي'), max_digits=15, decimal_places=2, default=0)
    total_debit = models.DecimalField(_('إجمالي المدين'), max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(_('إجمالي الدائن'), max_digits=15, decimal_places=2, default=0)
    closing_balance = models.DecimalField(_('الرصيد الختامي'), max_digits=15, decimal_places=2, default=0)
    balance_type = models.CharField(_('نوع الرصيد'), max_length=10, choices=[('DEBIT', _('مدين')), ('CREDIT', _('دائن'))], default='DEBIT')

    class Meta:
        verbose_name = _('ميزان مراجعة')
        verbose_name_plural = _('ميزان المراجعة')
        unique_together = ['date', 'account']

    def __str__(self):
        return f"{self.account} - {self.date}"


class FinancialPeriod(models.Model):
    """الفترات المالية"""
    PERIOD_TYPES = [
        ('DAILY', _('يومي')),
        ('MONTHLY', _('شهري')),
        ('YEARLY', _('سنوي')),
    ]

    period_type = models.CharField(_('نوع الفترة'), max_length=10, choices=PERIOD_TYPES)
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    is_closed = models.BooleanField(_('مغلق'), default=False)
    closed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('المغلق'))
    closed_at = models.DateTimeField(_('تاريخ الإغلاق'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('فترة مالية')
        verbose_name_plural = _('الفترات المالية')
        ordering = ['-end_date']

    def __str__(self):
        return f"{self.get_period_type_display()} - {self.start_date} إلى {self.end_date}"
