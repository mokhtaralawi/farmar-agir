"""
Accounting Services - قلب النظام المحاسبي المزدوج
جميع القيود تنشأ تلقائياً مع كل عملية مالية
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import JournalEntry, JournalEntryLine, LedgerEntry


class AccountingService:
    """خدمة محاسبية لإنشاء القيود المحاسبية تلقائياً"""

    @staticmethod
    @transaction.atomic
    def create_entry(description, reference_type, reference_id, user, entries_data):
        """
        إنشاء قيد محاسبي جديد
        entries_data: list of dicts with 'account_id', 'debit', 'credit', 'description'
        """
        if not entries_data:
            return None

        from agri_bridge.agri_bridge import settings
        import datetime

        journal = JournalEntry.objects.create(
            entry_number=AccountingService._generate_entry_number(),
            date=timezone.now().date(),
            time=timezone.now().time(),
            description=description,
            status='DRAFT',
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

        total_debit = Decimal('0')
        total_credit = Decimal('0')

        for data in entries_data:
            line = JournalEntryLine.objects.create(
                entry=journal,
                account_id=data['account_id'],
                description=data.get('description', ''),
                debit=data.get('debit', 0),
                credit=data.get('credit', 0),
                partner=data.get('partner'),
                partner_type=data.get('partner_type'),
                partner_obj_id=data.get('partner_id'),
                currency=data.get('currency'),
            )
            total_debit += line.debit
            total_credit += line.credit

        journal.total_debit = total_debit
        journal.total_credit = total_credit

        if total_debit == total_credit:
            journal.status = 'APPROVED'
            journal.approved_by = user
            journal.approved_at = timezone.now()
        else:
            journal.status = 'DRAFT'

        journal.save()

        # Create ledger entries
        AccountingService._create_ledger_entries(journal)

        return journal

    @staticmethod
    def _generate_entry_number():
        """توليد رقم قيد تلقائي"""
        from .models import JournalEntry
        last = JournalEntry.objects.order_by('-id').first()
        if last:
            next_num = int(last.entry_number.split('-')[-1]) + 1
        else:
            next_num = 1
        return f"JE-{timezone.now().strftime('%Y')}-{next_num:06d}"

    @staticmethod
    def _create_ledger_entries(journal):
        """إنشاء سجلات دفتر الأستاذ"""
        from .models import LedgerEntry
        for line in journal.lines.all():
            # Get previous balance
            last_ledger = LedgerEntry.objects.filter(account=line.account).order_by('-date', '-id').first()
            if last_ledger:
                prev_balance = last_ledger.balance
                prev_type = last_ledger.balance_type
            else:
                prev_balance = Decimal('0')
                prev_type = 'DEBIT'

            # Calculate new balance
            new_debit = prev_balance + line.debit if prev_type == 'DEBIT' else prev_balance - line.debit
            new_credit = prev_balance + line.credit if prev_type == 'CREDIT' else prev_balance - line.credit

            if new_debit >= new_credit:
                new_balance = new_debit - new_credit
                new_type = 'DEBIT'
            else:
                new_balance = new_credit - new_debit
                new_type = 'CREDIT'

            # Update account balance
            from core.models import Account
            account = line.account
            if new_type == 'DEBIT':
                account.balance = new_balance
            else:
                account.balance = -new_balance
            account.save()

            LedgerEntry.objects.create(
                account=line.account,
                journal_entry=journal,
                journal_line=line,
                date=journal.date,
                description=line.description or journal.description,
                debit=line.debit,
                credit=line.credit,
                balance=new_balance,
                balance_type=new_type,
            )

    @staticmethod
    @transaction.atomic
    def approve_entry(entry_id, user):
        """اعتماد قيد محاسبي"""
        from .models import JournalEntry
        entry = JournalEntry.objects.get(id=entry_id)
        if entry.total_debit != entry.total_credit:
            raise ValueError(_('القيد غير متوازن'))
        entry.status = 'APPROVED'
        entry.approved_by = user
        entry.approved_at = timezone.now()
        entry.save()
        return entry

    @staticmethod
    @transaction.atomic
    def post_entry(entry_id):
        """ترحيل قيد محاسبي"""
        from .models import JournalEntry
        entry = JournalEntry.objects.get(id=entry_id)
        if entry.status != 'APPROVED':
            raise ValueError(_('لا يمكن ترحيل قيد غير معتمد'))
        entry.status = 'POSTED'
        entry.save()
        return entry

    @staticmethod
    @transaction.atomic
    def create_receiving_entry(invoice, user):
        """إنشاء قيد استلام من مزارع"""
        from core.models import Account
        entries = [
            {
                'account_id': Account.objects.filter(name__icontains='مخزون').first().id,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f"استلام بضاعة - فاتورة {invoice.invoice_number}",
            },
            {
                'account_id': Account.objects.filter(name__icontains='الرعويون').first().id,
                'debit': 0,
                'credit': invoice.total_amount,
                'description': f"مستحقات مزارع - {invoice.farmer.name}",
                'partner': invoice.farmer,
                'partner_type': 'FARMER',
                'partner_id': invoice.farmer.id,
            },
        ]
        return AccountingService.create_entry(
            description=f"استلام بضاعة من {invoice.farmer.name}",
            reference_type='RECEIVING',
            reference_id=invoice.id,
            user=user,
            entries_data=entries,
        )

    @staticmethod
    @transaction.atomic
    def create_sales_entry(invoice, user):
        """إنشاء قيد بيع"""
        from core.models import Account
        entries = [
            {
                'account_id': Account.objects.filter(name__icontains='المقاوته').first().id,
                'debit': invoice.net_amount,
                'credit': 0,
                'description': f"مبيعات - فاتورة {invoice.invoice_number}",
                'partner': invoice.buyer,
                'partner_type': 'BUYER',
                'partner_id': invoice.buyer.id,
            },
            {
                'account_id': Account.objects.filter(name__icontains='عمولات').first().id,
                'debit': 0,
                'credit': invoice.total_amount - invoice.net_amount,
                'description': f"عمولة وسيط - فاتورة {invoice.invoice_number}",
            },
            {
                'account_id': Account.objects.filter(name__icontains='مخزون').first().id,
                'debit': 0,
                'credit': invoice.net_amount,
                'description': f"خصم مخزون - فاتورة {invoice.invoice_number}",
            },
        ]
        return AccountingService.create_entry(
            description=f"بيع للبائع {invoice.buyer.name}",
            reference_type='SALES',
            reference_id=invoice.id,
            user=user,
            entries_data=entries,
        )

    @staticmethod
    @transaction.atomic
    def create_collection_entry(receipt, user):
        """إنشاء قيد تحصيل"""
        from core.models import Account
        entries = [
            {
                'account_id': Account.objects.filter(name__icontains='الصندوق').first().id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f"قبض - سند {receipt.receipt_number}",
            },
            {
                'account_id': Account.objects.filter(name__icontains='المقاوته').first().id,
                'debit': 0,
                'credit': receipt.amount,
                'description': f"تحصيل من بائع - {receipt.buyer.name}",
                'partner': receipt.buyer,
                'partner_type': 'BUYER',
                'partner_id': receipt.buyer.id,
            },
        ]
        return AccountingService.create_entry(
            description=f"تحصيل من {receipt.buyer.name}",
            reference_type='COLLECTION',
            reference_id=receipt.id,
            user=user,
            entries_data=entries,
        )

    @staticmethod
    @transaction.atomic
    def create_payment_entry(voucher, user):
        """إنشاء قيد صرف"""
        from core.models import Account
        entries = [
            {
                'account_id': Account.objects.filter(name__icontains='الرعويون').first().id,
                'debit': voucher.amount,
                'credit': 0,
                'description': f"صرف - سند {voucher.voucher_number}",
                'partner': voucher.farmer,
                'partner_type': 'FARMER',
                'partner_id': voucher.farmer.id,
            },
            {
                'account_id': Account.objects.filter(name__icontains='الصندوق').first().id,
                'debit': 0,
                'credit': voucher.amount,
                'description': f"صرف لمزارع - {voucher.farmer.name}",
            },
        ]
        return AccountingService.create_entry(
            description=f"صرف مستحقات {voucher.farmer.name}",
            reference_type='PAYMENT',
            reference_id=voucher.id,
            user=user,
            entries_data=entries,
        )
