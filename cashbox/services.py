"""
Cashbox Services - خدمات الصندوق
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import CashBox, CashTransaction, DailyCashClosing


class CashBoxService:
    """خدمة إدارة الصناديق"""

    @staticmethod
    @transaction.atomic
    def cash_in(cashbox, amount, description, reference_type, reference_id, user):
        """إيداع في الصندوق"""
        if cashbox.status != 'OPEN':
            raise ValueError('الصندوق مغلق')

        balance_before = cashbox.current_balance
        cashbox.current_balance += amount
        cashbox.save()

        transaction_record = CashTransaction.objects.create(
            cashbox=cashbox,
            transaction_type='INCOME',
            amount=amount,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            balance_before=balance_before,
            balance_after=cashbox.current_balance,
            created_by=user,
        )

        return transaction_record

    @staticmethod
    @transaction.atomic
    def cash_out(cashbox, amount, description, reference_type, reference_id, user):
        """صرف من الصندوق"""
        if cashbox.status != 'OPEN':
            raise ValueError('الصندوق مغلق')

        if cashbox.current_balance < amount:
            raise ValueError(f'رصيد الصندوق ({cashbox.current_balance}) غير كافٍ للصرف ({amount})')

        balance_before = cashbox.current_balance
        cashbox.current_balance -= amount
        cashbox.save()

        transaction_record = CashTransaction.objects.create(
            cashbox=cashbox,
            transaction_type='EXPENSE',
            amount=amount,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            balance_before=balance_before,
            balance_after=cashbox.current_balance,
            created_by=user,
        )

        return transaction_record

    @staticmethod
    @transaction.atomic
    def transfer_between_boxes(from_box, to_box, amount, description, user):
        """تحويل بين صناديق"""
        if from_box.current_balance < amount:
            raise ValueError(f'رصيد الصندوق المصدر ({from_box.current_balance}) غير كافٍ')

        # Debit from source
        balance_before_from = from_box.current_balance
        from_box.current_balance -= amount
        from_box.save()

        CashTransaction.objects.create(
            cashbox=from_box,
            transaction_type='TRANSFER_OUT',
            amount=amount,
            description=description,
            balance_before=balance_before_from,
            balance_after=from_box.current_balance,
            created_by=user,
        )

        # Credit to destination
        balance_before_to = to_box.current_balance
        to_box.current_balance += amount
        to_box.save()

        CashTransaction.objects.create(
            cashbox=to_box,
            transaction_type='TRANSFER_IN',
            amount=amount,
            description=description,
            balance_before=balance_before_to,
            balance_after=to_box.current_balance,
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def daily_close(cashbox, user):
        """إقفال يومي للصندوق"""
        today = timezone.now().date()
        
        # Check if already closed
        if DailyCashClosing.objects.filter(cashbox=cashbox, date=today).exists():
            raise ValueError('تم إقفال الصندوق اليوم بالفعل')

        # Calculate totals
        today_transactions = CashTransaction.objects.filter(
            cashbox=cashbox,
            created_at__date=today,
            is_deleted=False,
        )

        total_income = sum(t.amount for t in today_transactions.filter(transaction_type='INCOME'))
        total_expense = sum(t.amount for t in today_transactions.filter(transaction_type='EXPENSE'))

        # Get opening balance (closing balance of previous day or initial)
        prev_closing = DailyCashClosing.objects.filter(cashbox=cashbox).order_by('-date').first()
        opening_balance = prev_closing.closing_balance if prev_closing else cashbox.opening_balance

        closing_balance = opening_balance + total_income - total_expense
        difference = closing_balance - cashbox.current_balance

        DailyCashClosing.objects.create(
            cashbox=cashbox,
            date=today,
            opening_balance=opening_balance,
            total_income=total_income,
            total_expense=total_expense,
            closing_balance=closing_balance,
            expected_balance=cashbox.current_balance,
            difference=difference,
            created_by=user,
        )

        # Close cashbox
        cashbox.status = 'CLOSED'
        cashbox.save()
