"""
Accounting Views - النظام المحاسبي المزدوج
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, Q
from .models import JournalEntry, JournalEntryLine, LedgerEntry, TrialBalance, FinancialPeriod


@login_required
def journal_entries(request):
    """قائمة القيود اليومية"""
    entries = JournalEntry.objects.filter(is_deleted=False).select_related('created_by')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    if date_from:
        entries = entries.filter(date__gte=date_from)
    if date_to:
        entries = entries.filter(date__lte=date_to)
    if status:
        entries = entries.filter(status=status)
    entries = entries.order_by('-created_at')
    return render(request, 'accounting/entries.html', {
        'entries': entries,
        'filters': {'date_from': date_from, 'date_to': date_to, 'status': status}
    })


@login_required
@transaction.atomic
def create_entry(request):
    """إنشاء قيد محاسبي"""
    if request.method == 'POST':
        date = request.POST.get('date')
        description = request.POST.get('description')
        lines = request.POST.getlist('lines[]')
        
        # Parse lines: account_id|debit|credit|description|partner_type|partner_id
        entries_data = []
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        for line_data in lines:
            parts = line_data.split('|')
            debit = Decimal(parts[1]) if parts[1] else Decimal('0')
            credit = Decimal(parts[2]) if parts[2] else Decimal('0')
            entries_data.append({
                'account_id': int(parts[0]),
                'debit': debit,
                'credit': credit,
                'description': parts[3] if len(parts) > 3 else '',
                'partner': None,
                'partner_type': parts[4] if len(parts) > 4 else None,
                'partner_id': int(parts[5]) if len(parts) > 5 and parts[5] else None,
                'currency': None,
            })
            total_debit += debit
            total_credit += credit

        if total_debit != total_credit:
            messages.error(request, f'القيد غير متوازن: مدين={total_debit} | دائن={total_credit}')
            return redirect('accounting:create')

        journal = JournalEntry.objects.create(
            entry_number=f"JE-{timezone.now().strftime('%Y')}-{JournalEntry.objects.count() + 1:06d}",
            date=date, description=description, status='DRAFT',
            created_by=request.user,
        )

        for data in entries_data:
            JournalEntryLine.objects.create(entry=journal, **data)

        journal.total_debit = total_debit
        journal.total_credit = total_credit
        journal.status = 'APPROVED'
        journal.approved_by = request.user
        journal.approved_at = timezone.now()
        journal.save()

        # Create ledger entries
        from accounting.services import AccountingService
        AccountingService._create_ledger_entries(journal)

        messages.success(request, 'تم إنشاء القيد بنجاح')
        return redirect('accounting:entries')

    from core.models import Account
    from partners.models import Farmer, Buyer
    return render(request, 'accounting/create.html', {
        'accounts': Account.objects.filter(is_active=True),
        'farmers': Farmer.objects.filter(status='ACTIVE'),
        'buyers': Buyer.objects.filter(status='ACTIVE'),
    })


@login_required
def entry_detail(request, pk):
    """تفاصيل قيد محاسبي"""
    entry = get_object_or_404(JournalEntry, id=pk, is_deleted=False)
    return render(request, 'accounting/entry_detail.html', {'entry': entry})


@login_required
def ledger(request):
    """دفتر الأستاذ"""
    from core.models import Account
    account_id = request.GET.get('account')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    ledger_entries = LedgerEntry.objects.all()
    if account_id:
        ledger_entries = ledger_entries.filter(account_id=account_id)
    if date_from:
        ledger_entries = ledger_entries.filter(date__gte=date_from)
    if date_to:
        ledger_entries = ledger_entries.filter(date__lte=date_to)
    ledger_entries = ledger_entries.order_by('date', 'id')

    return render(request, 'accounting/ledger.html', {
        'ledger': ledger_entries,
        'accounts': Account.objects.filter(is_active=True),
        'account_id': account_id,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def trial_balance(request):
    """ميزان المراجعة"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    ledger_entries = LedgerEntry.objects.all()
    if date_from:
        ledger_entries = ledger_entries.filter(date__gte=date_from)
    if date_to:
        ledger_entries = ledger_entries.filter(date__lte=date_to)

    from core.models import Account
    accounts = Account.objects.filter(is_active=True)
    balances = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    
    for account in accounts:
        acc_ledger = ledger_entries.filter(account=account)
        acct_debit = acc_ledger.aggregate(d=Sum('debit'))['d'] or 0
        acct_credit = acc_ledger.aggregate(c=Sum('credit'))['c'] or 0
        
        if acct_debit > 0 or acct_credit > 0:
            balance = acct_debit - acct_credit
            balances.append({
                'account': account,
                'debit': acct_debit,
                'credit': acct_credit,
                'balance': abs(balance),
                'balance_type': 'DEBIT' if balance >= 0 else 'CREDIT',
            })
            total_debit += acct_debit
            total_credit += acct_credit

    return render(request, 'accounting/trial_balance.html', {
        'balances': balances,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def account_chart(request):
    """شجرة الحسابات"""
    from core.models import Account
    accounts = Account.objects.filter(is_active=True).select_related('parent')
    # Build tree
    tree = []
    roots = accounts.filter(parent=None)
    
    def build_tree(parent, level=0):
        children = accounts.filter(parent=parent)
        for child in children:
            tree.append({'account': child, 'level': level})
            build_tree(child, level + 1)
    
    for root in roots:
        tree.append({'account': root, 'level': 0})
        build_tree(root, 1)
    
    return render(request, 'accounting/chart.html', {'tree': tree})


@login_required
@transaction.atomic
def close_period(request):
    """إغلاق فترة مالية"""
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        period_type = request.POST.get('period_type', 'MONTHLY')
        
        FinancialPeriod.objects.create(
            period_type=period_type, start_date=start_date, end_date=end_date,
            is_closed=True, closed_by=request.user, closed_at=timezone.now(),
        )
        
        messages.success(request, 'تم إغلاق الفترة المالية بنجاح')
        return redirect('accounting:close_period')

    return render(request, 'accounting/close_period.html', {
        'periods': FinancialPeriod.objects.all().order_by('-end_date'),
    })
