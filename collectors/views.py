"""
Collectors Views - التحصيل من المقاوته
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import CollectionReceipt
from partners.models import Buyer
from billing.models import SalesInvoice
from core.models import SystemSettings
from cashbox.models import CashBox
from cashbox.services import CashBoxService
from accounting.services import AccountingService


@login_required
def collectors_list(request):
    """قائمة سندات القبض"""
    receipts = CollectionReceipt.objects.filter(is_deleted=False).select_related('buyer', 'created_by')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    buyer_id = request.GET.get('buyer')
    if date_from:
        receipts = receipts.filter(date__gte=date_from)
    if date_to:
        receipts = receipts.filter(date__lte=date_to)
    if buyer_id:
        receipts = receipts.filter(buyer_id=buyer_id)
    receipts = receipts.order_by('-created_at')
    return render(request, 'collectors/list.html', {
        'receipts': receipts,
        'buyers': Buyer.objects.filter(status='ACTIVE'),
        'filters': {'date_from': date_from, 'date_to': date_to, 'buyer': buyer_id}
    })


@login_required
@transaction.atomic
def create_collection(request):
    """إنشاء سند قبض"""
    if request.method == 'POST':
        buyer_id = request.POST.get('buyer')
        payment_method = request.POST.get('payment_method', 'CASH')
        amount = Decimal(request.POST.get('amount', 0))
        discount = Decimal(request.POST.get('discount', 0) or 0)
        notes = request.POST.get('notes', '')
        try:
            buyer = Buyer.objects.get(id=buyer_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('collectors:create')

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('collectors:create')

        net = amount + discount
        if net > buyer.current_balance:
            messages.error(request, f'المبلغ ({amount}) + الخصم ({discount}) = {net} أكبر من رصيد الرعوي ({buyer.current_balance})')
            return redirect('collectors:create')

        last_receipt = CollectionReceipt.objects.order_by('-id').first()
        num = (int(last_receipt.receipt_number.split('-')[-1]) + 1) if last_receipt else 1
        receipt_number = f"COL-{timezone.now().strftime('%Y')}-{num:06d}"

        receipt = CollectionReceipt.objects.create(
            receipt_number=receipt_number, buyer=buyer, payment_method=payment_method,
            amount=amount, discount=discount, net_amount=net, notes=notes,
            date=timezone.now().date(), created_by=request.user,
        )

        # Update buyer balance - deduct amount + discount
        buyer.current_balance -= net
        buyer.total_paid += amount
        buyer.total_remaining -= net
        buyer.save()

        # Cash in
        try:
            if payment_method == 'CASH':
                cashbox = CashBox.objects.filter(status='OPEN').first()
                if cashbox:
                    CashBoxService.cash_in(
                        cashbox=cashbox, amount=amount,
                        description=f"تحصيل - {receipt_number}",
                        reference_type='COLLECTION', reference_id=receipt.id,
                        user=request.user,
                    )
        except:
            pass

        # Accounting entry
        try:
            AccountingService.create_collection_entry(receipt, request.user)
        except:
            pass

        messages.success(request, f'تم إنشاء سند قبض {receipt_number} بنجاح')
        from core.activity import log_activity
        log_activity(request, 'COLLECTION_CREATE', f'إنشاء سند قبض {receipt_number} من المقوت {buyer.name} بقيمة {amount}' + (f' (خصم: {discount})' if discount else ''), 'CollectionReceipt', receipt.id)
        return redirect('collectors:print', receipt.id)

    return render(request, 'collectors/create.html', {
        'buyers': Buyer.objects.filter(status='ACTIVE'),
    })


@login_required
def print_collection(request, pk):
    """طباعة سند القبض"""
    receipt = get_object_or_404(CollectionReceipt, id=pk, is_deleted=False)
    settings = SystemSettings.get_settings()
    discount_line = f'<p style="color:#c62828;">الخصم: -{receipt.discount}</p>' if receipt.discount else ''
    net = receipt.net_amount if receipt.net_amount else receipt.amount
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8">
    <style>@media print {{ body {{ width: 58mm; font-size: 10px; }} }}
    body {{ font-family: sans-serif; margin: 0; padding: 5px; }}
    .header {{ text-align: center; border-bottom: 1px dashed #000; padding-bottom: 5px; }}
    .info {{ margin: 5px 0; font-size: 9px; text-align: center; }}
    .total {{ border-top: 1px dashed #000; padding-top: 5px; font-weight: bold; text-align: center; }}
    </style></head><body>
    <div class="header"><h3>{settings.company_name}</h3><p>سند قبض</p></div>
    <div class="info">
    <p>رقم: {receipt.receipt_number}</p>
    <p>الرعوي: {receipt.buyer.name}</p>
    <p>المبلغ: {receipt.amount}</p>
    {discount_line}
    <p style="font-weight:bold;">الصافي: {net}</p>
    <p>الطريقة: {receipt.get_payment_method_display()}</p>
    <p>التاريخ: {receipt.date}</p>
    <p>الموظف: {receipt.created_by}</p>
    <p>الرصيد الحالي: {receipt.buyer.current_balance}</p>
    </div>
    <div class="total">
        <p>شكراً لكم</p>
        <p style="font-size:7px;color:#888;">تمت الطباعة بواسطة: {request.user.get_full_name() or request.user.username}</p>
    </div>
    </body></html>"""
    return HttpResponse(html, content_type='text/html')


@login_required
def buyer_statement(request, buyer_id):
    """كشف حساب الرعوي"""
    buyer = get_object_or_404(Buyer, id=buyer_id)
    sales = SalesInvoice.objects.filter(buyer=buyer, status='APPROVED', is_deleted=False)
    receipts = CollectionReceipt.objects.filter(buyer=buyer, is_deleted=False)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        sales = sales.filter(date__gte=date_from)
        receipts = receipts.filter(date__gte=date_from)
    if date_to:
        sales = sales.filter(date__lte=date_to)
        receipts = receipts.filter(date__lte=date_to)

    return render(request, 'collectors/buyer_statement.html', {
        'buyer': buyer,
        'sales': sales.order_by('-date'),
        'receipts': receipts.order_by('-date'),
        'date_from': date_from,
        'date_to': date_to,
    })
