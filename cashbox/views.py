"""
Cashbox Views - إدارة الصناديق
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import CashBox, CashTransaction, DailyCashClosing
from core.models import SystemSettings
from .services import CashBoxService


@login_required
def cashbox_list(request):
    """قائمة الصناديق"""
    boxes = CashBox.objects.all()
    return render(request, 'cashbox/list.html', {'boxes': boxes})


@login_required
@transaction.atomic
def cash_in(request):
    """إيداع في الصندوق"""
    if request.method == 'POST':
        cashbox_id = request.POST.get('cashbox')
        amount = Decimal(request.POST.get('amount', 0))
        description = request.POST.get('description', '')
        try:
            cashbox = CashBox.objects.get(id=cashbox_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('cashbox:cash_in')

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('cashbox:cash_in')

        CashBoxService.cash_in(
            cashbox=cashbox, amount=amount, description=description,
            reference_type='MANUAL', reference_id=None, user=request.user,
        )

        messages.success(request, f'تم الإيداع {amount} بنجاح')
        return redirect('cashbox:cash_in')

    return render(request, 'cashbox/cash_in.html', {
        'boxes': CashBox.objects.filter(status='OPEN'),
    })


@login_required
@transaction.atomic
def cash_out(request):
    """صرف من الصندوق"""
    if request.method == 'POST':
        cashbox_id = request.POST.get('cashbox')
        amount = Decimal(request.POST.get('amount', 0))
        description = request.POST.get('description', '')
        try:
            cashbox = CashBox.objects.get(id=cashbox_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('cashbox:cash_out')

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('cashbox:cash_out')

        CashBoxService.cash_out(
            cashbox=cashbox, amount=amount, description=description,
            reference_type='MANUAL', reference_id=None, user=request.user,
        )

        messages.success(request, f'تم الصرف {amount} بنجاح')
        return redirect('cashbox:cash_out')

    return render(request, 'cashbox/cash_out.html', {
        'boxes': CashBox.objects.filter(status='OPEN'),
    })


@login_required
@transaction.atomic
def transfer(request):
    """تحويل بين صناديق"""
    if request.method == 'POST':
        from_id = request.POST.get('from_box')
        to_id = request.POST.get('to_box')
        amount = Decimal(request.POST.get('amount', 0))
        description = request.POST.get('description', '')
        try:
            from_box = CashBox.objects.get(id=from_id)
            to_box = CashBox.objects.get(id=to_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('cashbox:transfer')

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('cashbox:transfer')

        CashBoxService.transfer_between_boxes(from_box, to_box, amount, description, request.user)

        messages.success(request, f'تم التحويل {amount} بنجاح')
        return redirect('cashbox:transfer')

    return render(request, 'cashbox/transfer.html', {
        'boxes': CashBox.objects.filter(status='OPEN'),
    })


@login_required
@transaction.atomic
def daily_close(request):
    """إقفال يومي"""
    if request.method == 'POST':
        cashbox_id = request.POST.get('cashbox')
        try:
            cashbox = CashBox.objects.get(id=cashbox_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('cashbox:daily_close')

        CashBoxService.daily_close(cashbox, request.user)
        messages.success(request, 'تم إقفال الصندوق بنجاح')
        return redirect('cashbox:list')

    return render(request, 'cashbox/daily_close.html', {
        'boxes': CashBox.objects.filter(status='OPEN'),
    })


@login_required
def cash_transactions(request, cashbox_id):
    """حركات صندوق معين"""
    cashbox = get_object_or_404(CashBox, id=cashbox_id)
    transactions = CashTransaction.objects.filter(cashbox=cashbox, is_deleted=False).order_by('-created_at')
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    return render(request, 'cashbox/transactions.html', {
        'cashbox': cashbox,
        'transactions': transactions,
        'date_from': date_from,
        'date_to': date_to,
    })
