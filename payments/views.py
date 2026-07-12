"""
Payments Views - صرف مستحقات الرعية
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from .models import PaymentVoucher, FarmerSettlement, DailySettlement
from partners.models import Farmer
from receiving.models import ReceivingInvoice
from core.models import SystemSettings
from cashbox.models import CashBox
from cashbox.services import CashBoxService
from accounting.services import AccountingService


@login_required
def payments_list(request):
    """قائمة سندات الصرف"""
    vouchers = PaymentVoucher.objects.filter(is_deleted=False).select_related('farmer', 'created_by')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    farmer_id = request.GET.get('farmer')
    if date_from:
        vouchers = vouchers.filter(date__gte=date_from)
    if date_to:
        vouchers = vouchers.filter(date__lte=date_to)
    if farmer_id:
        vouchers = vouchers.filter(farmer_id=farmer_id)
    vouchers = vouchers.order_by('-created_at')
    return render(request, 'payments/list.html', {
        'vouchers': vouchers,
        'farmers': Farmer.objects.filter(status='ACTIVE'),
        'filters': {'date_from': date_from, 'date_to': date_to, 'farmer': farmer_id}
    })


@login_required
@transaction.atomic
def create_payment(request):
    """إنشاء سند صرف"""
    if request.method == 'POST':
        farmer_id = request.POST.get('farmer')
        payment_method = request.POST.get('payment_method', 'CASH')
        amount = Decimal(request.POST.get('amount', 0))
        notes = request.POST.get('notes', '')
        try:
            farmer = Farmer.objects.get(id=farmer_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('payments:create')

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('payments:create')

        if amount > farmer.current_balance:
            messages.error(request, f'المبلغ ({amount}) أكبر من رصيد الرعوي ({farmer.current_balance})')
            return redirect('payments:create')

        last_voucher = PaymentVoucher.objects.order_by('-id').first()
        num = (int(last_voucher.voucher_number.split('-')[-1]) + 1) if last_voucher else 1
        voucher_number = f"PAY-{timezone.now().strftime('%Y')}-{num:06d}"

        voucher = PaymentVoucher.objects.create(
            voucher_number=voucher_number, farmer=farmer, payment_method=payment_method,
            amount=amount, notes=notes, date=timezone.now().date(), created_by=request.user,
        )

        # Update farmer balance
        farmer.current_balance -= amount
        farmer.total_paid += amount
        farmer.save()

        # Cash out
        try:
            if payment_method == 'CASH':
                cashbox = CashBox.objects.filter(status='OPEN').first()
                if cashbox:
                    CashBoxService.cash_out(
                        cashbox=cashbox, amount=amount,
                        description=f"صرف - {voucher_number}",
                        reference_type='PAYMENT', reference_id=voucher.id,
                        user=request.user,
                    )
        except:
            pass

        # Accounting entry
        try:
            AccountingService.create_payment_entry(voucher, request.user)
        except:
            pass

        messages.success(request, f'تم إنشاء سند صرف {voucher_number} بنجاح')
        from core.activity import log_activity
        log_activity(request, 'PAYMENT_CREATE', f'إنشاء سند صرف {voucher_number} للرعوي {farmer.name} بقيمة {amount}', 'PaymentVoucher', voucher.id)
        return redirect('payments:print', voucher.id)

    return render(request, 'payments/create.html', {
        'farmers': Farmer.objects.filter(status='ACTIVE'),
    })


@login_required
def print_payment(request, pk):
    """طباعة سند الصرف"""
    voucher = get_object_or_404(PaymentVoucher, id=pk, is_deleted=False)
    settings = SystemSettings.get_settings()
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8">
    <style>@media print {{ body {{ width: 58mm; font-size: 10px; }} }}
    body {{ font-family: sans-serif; margin: 0; padding: 5px; }}
    .header {{ text-align: center; border-bottom: 1px dashed #000; padding-bottom: 5px; }}
    .info {{ margin: 5px 0; font-size: 9px; text-align: center; }}
    .total {{ border-top: 1px dashed #000; padding-top: 5px; font-weight: bold; text-align: center; }}
    </style></head><body>
    <div class="header"><h3>{settings.company_name}</h3><p>سند صرف</p></div>
    <div class="info">
    <p>رقم: {voucher.voucher_number}</p>
    <p>الرعوي: {voucher.farmer.name}</p>
    <p>المبلغ: {voucher.amount}</p>
    <p>الطريقة: {voucher.get_payment_method_display()}</p>
    <p>التاريخ: {voucher.date}</p>
    <p>الموظف: {voucher.created_by}</p>
    </div>
    <div class="total">
        <p>شكراً لكم</p>
        <p style="font-size:7px;color:#888;">تمت الطباعة بواسطة: {request.user.get_full_name() or request.user.username}</p>
    </div>
    </body></html>"""
    return HttpResponse(html, content_type='text/html')


@login_required
def farmer_statement(request, farmer_id):
    """كشف حساب الرعوي"""
    farmer = get_object_or_404(Farmer, id=farmer_id)
    receiving = ReceivingInvoice.objects.filter(farmer=farmer, status='APPROVED', is_deleted=False)
    payments = PaymentVoucher.objects.filter(farmer=farmer, is_deleted=False)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        receiving = receiving.filter(date__gte=date_from)
        payments = payments.filter(date__gte=date_from)
    if date_to:
        receiving = receiving.filter(date__lte=date_to)
        payments = payments.filter(date__lte=date_to)

    return render(request, 'payments/farmer_statement.html', {
        'farmer': farmer,
        'receiving': receiving.order_by('-date'),
        'payments': payments.order_by('-date'),
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def settlements_list(request):
    """قائمة التسويات"""
    settlements = FarmerSettlement.objects.filter(is_deleted=False).select_related('farmer', 'created_by')
    settlements = settlements.order_by('-created_at')
    return render(request, 'payments/settlements.html', {'settlements': settlements})


@login_required
@transaction.atomic
def create_settlement(request):
    """إنشاء تسوية مع رعوي"""
    if request.method == 'POST':
        farmer_id = request.POST.get('farmer')
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        try:
            farmer = Farmer.objects.get(id=farmer_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('payments:create_settlement')

        # Calculate totals for the period
        total_sales = ReceivingInvoice.objects.filter(
            farmer=farmer, date__gte=period_start, date__lte=period_end,
            status='APPROVED', is_deleted=False
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        commissions = (total_sales * Decimal('0.05'))  # 5% commission
        discounts = Decimal('0')
        expenses = Decimal('0')
        total_paid = PaymentVoucher.objects.filter(
            farmer=farmer, date__gte=period_start, date__lte=period_end, is_deleted=False
        ).aggregate(total=Sum('amount'))['total'] or 0

        net_payable = total_sales - commissions - discounts - expenses - total_paid

        last_settlement = FarmerSettlement.objects.order_by('-id').first()
        num = (int(last_settlement.settlement_number.split('-')[-1]) + 1) if last_settlement else 1
        settlement_number = f"SETT-{num:06d}"

        settlement = FarmerSettlement.objects.create(
            settlement_number=settlement_number, farmer=farmer,
            period_start=period_start, period_end=period_end,
            total_sales=total_sales, total_commissions=commissions,
            total_discounts=discounts, total_expenses=expenses,
            total_paid=total_paid, net_payable=net_payable,
            created_by=request.user, status='APPROVED',
        )

        # Create daily settlements
        current_date = timezone.datetime.strptime(period_start, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(period_end, '%Y-%m-%d').date()
        while current_date <= end_date:
            daily_receiving = ReceivingInvoice.objects.filter(
                farmer=farmer, date=current_date, status='APPROVED'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            daily_commission = daily_receiving * Decimal('0.05')
            daily_net = daily_receiving - daily_commission

            DailySettlement.objects.create(
                farmer=farmer, date=current_date,
                received_value=daily_receiving,
                sold_value=daily_receiving,
                commission=daily_commission,
                net_amount=daily_net,
                is_settled=True,
                settlement=settlement,
            )
            current_date += timedelta(days=1)

        # Update farmer balance
        farmer.current_balance -= net_payable
        farmer.save()

        messages.success(request, f'تم إنشاء تسوية {settlement_number} بنجاح')
        from core.activity import log_activity
        log_activity(request, 'SETTLEMENT_CREATE', f'إنشاء تسوية {settlement_number} للرعوي {farmer.name} بقيمة {net_payable}', 'Settlement', settlement.id)
        return redirect('payments:settlements')

    return render(request, 'payments/create_settlement.html', {
        'farmers': Farmer.objects.filter(status='ACTIVE'),
    })
