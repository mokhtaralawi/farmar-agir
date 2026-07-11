"""
Expenses Views - إدارة المصروفات
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import Expense, ExpenseCategory
from core.models import SystemSettings
from cashbox.models import CashBox
from cashbox.services import CashBoxService
from accounting.services import AccountingService


@login_required
def expenses_list(request):
    """قائمة المصروفات"""
    expenses = Expense.objects.filter(is_deleted=False).select_related('category', 'created_by')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    expenses = expenses.order_by('-date')
    return render(request, 'expenses/list.html', {
        'expenses': expenses,
        'categories': ExpenseCategory.objects.filter(is_active=True),
        'filters': {'date_from': date_from, 'date_to': date_to, 'category': category_id}
    })


@login_required
@transaction.atomic
def create_expense(request):
    """إنشاء مصروف"""
    if request.method == 'POST':
        category_id = request.POST.get('category')
        payment_method = request.POST.get('payment_method', 'CASH')
        amount = Decimal(request.POST.get('amount', 0))
        beneficiary = request.POST.get('beneficiary', '')
        notes = request.POST.get('notes', '')
        try:
            category = ExpenseCategory.objects.get(id=category_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('expenses:create')

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('expenses:create')

        last_expense = Expense.objects.order_by('-id').first()
        num = (int(last_expense.voucher_number.split('-')[-1]) + 1) if last_expense else 1
        voucher_number = f"EXP-{timezone.now().strftime('%Y')}-{num:06d}"

        expense = Expense.objects.create(
            voucher_number=voucher_number, category=category, payment_method=payment_method,
            amount=amount, beneficiary=beneficiary, notes=notes,
            date=timezone.now().date(), created_by=request.user,
        )

        # Cash out
        try:
            if payment_method == 'CASH':
                cashbox = CashBox.objects.filter(status='OPEN').first()
                if cashbox:
                    CashBoxService.cash_out(
                        cashbox=cashbox, amount=amount,
                        description=f"مصروف - {voucher_number} - {category.name}",
                        reference_type='EXPENSE', reference_id=expense.id,
                        user=request.user,
                    )
        except:
            pass

        # Accounting entry
        try:
            from core.models import Account, AccountType
            expense_account_type = AccountType.objects.filter(account_type='EXPENSES').first()
            expense_account = Account.objects.filter(account_type=expense_account_type).first() if expense_account_type else None
            cash_account = Account.objects.filter(name__icontains='الصندوق').first()
            
            if expense_account and cash_account:
                entries = [
                    {'account_id': expense_account.id,
                     'debit': amount, 'credit': 0, 'description': f"مصروف - {category.name}"},
                    {'account_id': cash_account.id,
                     'debit': 0, 'credit': amount, 'description': f"صرف مصروف - {category.name}"},
                ]
                AccountingService.create_entry(
                    description=f"مصروف: {category.name} - {beneficiary}",
                    reference_type='EXPENSE', reference_id=expense.id,
                    user=request.user, entries_data=entries,
                )
        except:
            pass

        messages.success(request, f'تم إنشاء مصروف {voucher_number} بنجاح')
        return redirect('expenses:list')

    return render(request, 'expenses/create.html', {
        'categories': ExpenseCategory.objects.filter(is_active=True),
    })
