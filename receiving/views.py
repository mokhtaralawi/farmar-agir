"""
Receiving Views - استلام المنتجات من الرعية
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import ReceivingInvoice, ReceivingItem, ReturnInvoice, ReturnItem
from partners.models import Farmer
from core.models import Warehouse, SystemSettings
from cashbox.models import CashBox
from inventory.services import InventoryService
from accounting.services import AccountingService
from cashbox.services import CashBoxService
from products.models import Product, Unit


@login_required
def receiving_list(request):
    """قائمة فواتير الاستلام"""
    invoices = ReceivingInvoice.objects.filter(is_deleted=False).select_related('farmer', 'created_by')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    farmer_id = request.GET.get('farmer')
    status = request.GET.get('status')
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    if farmer_id:
        invoices = invoices.filter(farmer_id=farmer_id)
    if status:
        invoices = invoices.filter(status=status)
    invoices = invoices.order_by('-created_at')
    return render(request, 'receiving/list.html', {
        'invoices': invoices,
        'farmers': Farmer.objects.filter(status='ACTIVE'),
        'filters': {'date_from': date_from, 'date_to': date_to, 'farmer': farmer_id, 'status': status}
    })


@login_required
@transaction.atomic
def create_receiving(request):
    """إنشاء فاتورة استلام"""
    if request.method == 'POST':
        farmer_id = request.POST.get('farmer')
        farmer_name = request.POST.get('farmer_name', '').strip()
        warehouse_id = request.POST.get('warehouse')
        try:
            if farmer_id:
                farmer = Farmer.objects.get(id=farmer_id)
            elif farmer_name:
                farmer = Farmer.objects.get(name=farmer_name)
            else:
                raise ValueError
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except:
            messages.error(request, 'يجب اختيار المزرع والمخزن')
            return redirect('receiving:create')

        date = request.POST.get('date')
        notes = request.POST.get('notes', '')
        items = request.POST.getlist('items[]')

        discount = Decimal(request.POST.get('discount', 0) or 0)

        last_invoice = ReceivingInvoice.objects.order_by('-id').first()
        num = (int(last_invoice.invoice_number.split('-')[-1]) + 1) if last_invoice else 1
        invoice_number = f"RCV-{timezone.now().strftime('%Y')}-{num:06d}"

        invoice = ReceivingInvoice.objects.create(
            invoice_number=invoice_number, farmer=farmer, warehouse=warehouse,
            date=date, notes=notes, status='APPROVED', created_by=request.user,
            approved_by=request.user, approved_at=timezone.now(),
        )

        total = Decimal('0')
        for item_data in items:
            parts = item_data.split('|')
            if len(parts) < 4 or not parts[0].strip():
                continue
            product = Product.objects.get(id=parts[0])
            unit_id = parts[1].strip() if len(parts) > 1 else ''
            unit = Unit.objects.get(id=unit_id) if unit_id else None
            quantity = Decimal(parts[2])
            price = Decimal(parts[3])
            item_total = quantity * price
            ReceivingItem.objects.create(
                invoice=invoice, product=product, unit=unit,
                quantity=quantity, unit_price=price, total=item_total,
            )
            total += item_total

        if discount > total:
            discount = total

        net = total - discount
        invoice.total_amount = total
        invoice.discount = discount
        invoice.net_amount = net
        invoice.save()

        # Update farmer balance with net amount
        farmer.current_balance += net
        farmer.total_receivables += net
        farmer.save()

        # Update inventory
        for item in invoice.items.all():
            InventoryService.receive_product(
                product=item.product, warehouse=warehouse,
                quantity=item.quantity, price=item.unit_price,
                user=request.user, reference_type='RECEIVING', reference_id=invoice.id,
            )

        # Create accounting entry
        try:
            AccountingService.create_receiving_entry(invoice, request.user)
        except:
            pass

        messages.success(request, f'تم إنشاء فاتورة استلام {invoice_number} بنجاح')
        return redirect('receiving:print', invoice.id)

    return render(request, 'receiving/create.html', {
        'farmers': Farmer.objects.filter(status='ACTIVE'),
        'warehouses': Warehouse.objects.filter(is_active=True),
        'products': Product.objects.filter(is_active=True),
        'units': Unit.objects.filter(is_active=True),
        'today': timezone.now().strftime('%Y-%m-%d'),
    })


@login_required
@transaction.atomic
def edit_receiving(request, pk):
    """تعديل فاتورة استلام"""
    invoice = get_object_or_404(ReceivingInvoice, id=pk, is_deleted=False)
    old_net = invoice.net_amount or invoice.total_amount

    if request.method == 'POST':
        discount = Decimal(request.POST.get('discount', 0) or 0)
        notes = request.POST.get('notes', '')

        total = sum(item.total for item in invoice.items.all())
        if discount > total:
            discount = total
        net = total - discount

        invoice.discount = discount
        invoice.net_amount = net
        invoice.notes = notes
        invoice.save()

        # Update farmer balance: reverse old, apply new
        farmer = invoice.farmer
        farmer.current_balance = farmer.current_balance - old_net + net
        farmer.total_receivables = farmer.total_receivables - old_net + net
        farmer.save()

        messages.success(request, f'تم تعديل فاتورة {invoice.invoice_number} بنجاح')
        return redirect('receiving:detail', invoice.id)

    return render(request, 'receiving/edit.html', {
        'invoice': invoice,
        'products': Product.objects.filter(is_active=True),
        'units': Unit.objects.filter(is_active=True),
    })


@login_required
def receiving_detail(request, pk):
    """تفاصيل فاتورة الاستلام"""
    invoice = get_object_or_404(ReceivingInvoice, id=pk, is_deleted=False)
    return render(request, 'receiving/detail.html', {
        'invoice': invoice,
    })


@login_required
def print_receiving(request, pk):
    """طباعة فاتورة الاستلام"""
    invoice = get_object_or_404(ReceivingInvoice, id=pk, is_deleted=False)
    settings = SystemSettings.get_settings()
    farmer = invoice.farmer
    discount_line = f'<p style="color:#c62828;">الخصم: -{invoice.discount}</p>' if invoice.discount else ''
    net = invoice.net_amount if invoice.net_amount else invoice.total_amount
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8">
    <style>@media print {{ body {{ width: 58mm; font-size: 10px; }} }}
    body {{ font-family: sans-serif; margin: 0; padding: 5px; }}
    .header {{ text-align: center; border-bottom: 1px dashed #000; padding-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
    th, td {{ border: 1px solid #ccc; padding: 2px; text-align: center; }}
    .total {{ border-top: 1px dashed #000; padding-top: 5px; font-weight: bold; text-align: center; }}
    .balance {{ border-top: 1px dashed #000; padding-top: 5px; text-align: center; font-size: 9px; }}
    </style></head><body>
    <div class="header"><h3>{settings.company_name}</h3><p>فاتورة استلام</p></div>
    <p style="text-align:center;font-size:9px;">رقم: {invoice.invoice_number}</p>
    <p style="text-align:center;font-size:9px;">الرعوي: {farmer.name}</p>
    <p style="text-align:center;font-size:9px;">التاريخ: {invoice.date}</p>
    <table><thead><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead>
    <tbody>{''.join(f'<tr><td>{i.product.name}</td><td>{i.quantity}</td><td>{i.unit_price}</td><td>{i.total}</td></tr>' for i in invoice.items.all())}</tbody></table>
    <div class="total">
        <p>الإجمالي: {invoice.total_amount}</p>
        {discount_line}
        <p style="font-size:14px;">الصافي: {net}</p>
    </div>
    <div class="balance">
        <p>المبلغ لأجله: {net}</p>
        <p>الرصيد الحالي: {farmer.current_balance}</p>
    </div>
    <p style="text-align:center;font-size:8px;">شكراً لكم</p>
    <p style="text-align:center;font-size:7px;color:#888;">تمت الطباعة بواسطة: {request.user.get_full_name() or request.user.username}</p>
    </body></html>"""
    return HttpResponse(html, content_type='text/html')


@login_required
@transaction.atomic
def create_return(request):
    """مرتجع استلام"""
    if request.method == 'POST':
        receiving_id = request.POST.get('receiving_invoice')
        farmer_id = request.POST.get('farmer')
        items = request.POST.getlist('items[]')
        try:
            original_invoice = ReceivingInvoice.objects.get(id=receiving_id)
            farmer = Farmer.objects.get(id=farmer_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('receiving:return')

        last_return = ReturnInvoice.objects.order_by('-id').first()
        num = (int(last_return.invoice_number.split('-')[-1]) + 1) if last_return else 1
        invoice_number = f"RCV-RET-{num:06d}"

        return_invoice = ReturnInvoice.objects.create(
            invoice_number=invoice_number, receiving_invoice=original_invoice,
            farmer=farmer, date=timezone.now().date(), created_by=request.user, status='APPROVED',
        )

        total = Decimal('0')
        for item_data in items:
            parts = item_data.split('|')
            product = Product.objects.get(id=parts[0])
            quantity = Decimal(parts[1])
            price = Decimal(parts[2])
            item_total = quantity * price
            ReturnItem.objects.create(
                return_invoice=return_invoice, product=product,
                quantity=quantity, unit_price=price, total=item_total,
            )
            total += item_total

        return_invoice.total_amount = total
        return_invoice.save()

        farmer.current_balance -= total
        farmer.total_receivables -= total
        farmer.save()

        messages.success(request, f'تم إنشاء مرتجع {invoice_number} بنجاح')
        return redirect('receiving:list')

    return render(request, 'receiving/return.html', {
        'invoices': ReceivingInvoice.objects.filter(status='APPROVED', is_deleted=False),
        'farmers': Farmer.objects.filter(status='ACTIVE'),
    })
