"""
Billing Views - بيع المنتجات للباعة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import SalesInvoice, SalesItem, SalesReturn, SalesReturnItem
from partners.models import Buyer
from core.models import Warehouse, SystemSettings
from cashbox.models import CashBox
from products.models import Product, Unit
from inventory.services import InventoryService
from accounting.services import AccountingService


@login_required
def sales_list(request):
    """قائمة فواتير البيع"""
    invoices = SalesInvoice.objects.filter(is_deleted=False).select_related('buyer', 'created_by')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    buyer_id = request.GET.get('buyer')
    status = request.GET.get('status')
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    if buyer_id:
        invoices = invoices.filter(buyer_id=buyer_id)
    if status:
        invoices = invoices.filter(status=status)
    invoices = invoices.order_by('-created_at')
    return render(request, 'billing/list.html', {
        'invoices': invoices,
        'buyers': Buyer.objects.filter(status='ACTIVE'),
        'filters': {'date_from': date_from, 'date_to': date_to, 'buyer': buyer_id, 'status': status}
    })


@login_required
@transaction.atomic
def create_sale(request):
    """إنشاء فاتورة بيع"""
    if request.method == 'POST':
        buyer_id = request.POST.get('buyer')
        warehouse_id = request.POST.get('warehouse')
        date = request.POST.get('date')
        notes = request.POST.get('notes', '')
        items = request.POST.getlist('items[]')
        try:
            buyer = Buyer.objects.get(id=buyer_id)
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('billing:create')

        # Check credit limit
        total = sum(Decimal(parts[2]) * Decimal(parts[3]) - Decimal(parts[4] or '0') for parts in [i.split('|') for i in items])
        if buyer.credit_limit > 0 and (buyer.current_balance + total) > buyer.credit_limit:
            messages.error(request, f'تجاوز الحد الائتماني ({buyer.credit_limit})')
            return redirect('billing:create')

        last_invoice = SalesInvoice.objects.order_by('-id').first()
        num = (int(last_invoice.invoice_number.split('-')[-1]) + 1) if last_invoice else 1
        invoice_number = f"SALE-{timezone.now().strftime('%Y')}-{num:06d}"

        invoice = SalesInvoice.objects.create(
            invoice_number=invoice_number, buyer=buyer, warehouse=warehouse,
            date=date, notes=notes, status='APPROVED', created_by=request.user,
            approved_by=request.user, approved_at=timezone.now(),
        )

        invoice_total = Decimal('0')
        invoice_discount = Decimal('0')
        for item_data in items:
            parts = item_data.split('|')
            product = Product.objects.get(id=parts[0])
            unit_id = parts[1].strip() if len(parts) > 1 else ''
            unit = Unit.objects.get(id=unit_id) if unit_id else None
            quantity = Decimal(parts[2])
            price = Decimal(parts[3])
            discount = Decimal(parts[4] or '0')
            item_total = (quantity * price) - discount

            # Check inventory
            try:
                InventoryService.sell_product(
                    product=product, warehouse=warehouse,
                    quantity=quantity, price=price,
                    user=request.user, reference_type='SALES', reference_id=invoice.id,
                )
            except ValueError as e:
                messages.error(request, str(e))
                invoice.delete()
                return redirect('billing:create')

            SalesItem.objects.create(
                invoice=invoice, product=product, unit=unit,
                quantity=quantity, unit_price=price, discount=discount, total=item_total,
            )
            invoice_total += (quantity * price)
            invoice_discount += discount

        invoice.total_amount = invoice_total
        invoice.total_discount = invoice_discount
        invoice.net_amount = invoice_total - invoice_discount
        invoice.save()

        # Update buyer balance
        buyer.current_balance += invoice.net_amount
        buyer.total_purchases += invoice.net_amount
        buyer.total_remaining += invoice.net_amount
        buyer.save()

        # Create accounting entry
        try:
            AccountingService.create_sales_entry(invoice, request.user)
        except:
            pass

        messages.success(request, f'تم إنشاء فاتورة بيع {invoice_number} بنجاح')
        return redirect('billing:print', invoice.id)

    return render(request, 'billing/create.html', {
        'buyers': Buyer.objects.filter(status='ACTIVE'),
        'warehouses': Warehouse.objects.filter(is_active=True),
        'products': Product.objects.filter(is_active=True),
        'units': Unit.objects.filter(is_active=True),
    })


@login_required
def print_sale(request, pk):
    """طباعة فاتورة البيع"""
    invoice = get_object_or_404(SalesInvoice, id=pk, is_deleted=False)
    settings = SystemSettings.get_settings()
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8">
    <style>@media print {{ body {{ width: 58mm; font-size: 10px; }} }}
    body {{ font-family: sans-serif; margin: 0; padding: 5px; }}
    .header {{ text-align: center; border-bottom: 1px dashed #000; padding-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
    th, td {{ border: 1px solid #ccc; padding: 2px; text-align: center; }}
    .total {{ border-top: 1px dashed #000; padding-top: 5px; font-weight: bold; text-align: center; }}
    </style></head><body>
    <div class="header"><h3>{settings.company_name}</h3><p>فاتورة بيع</p></div>
    <p style="text-align:center;font-size:9px;">رقم: {invoice.invoice_number}</p>
    <p style="text-align:center;font-size:9px;">الرعوي: {invoice.buyer.name}</p>
    <p style="text-align:center;font-size:9px;">التاريخ: {invoice.date}</p>
    <table><thead><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الخصم</th><th>الإجمالي</th></tr></thead>
    <tbody>{''.join(f'<tr><td>{i.product.name}</td><td>{i.quantity}</td><td>{i.unit_price}</td><td>{i.discount}</td><td>{i.total}</td></tr>' for i in invoice.items.all())}</tbody></table>
    <div class="total"><p>الإجمالي: {invoice.total_amount}</p><p>الخصم: {invoice.total_discount}</p><p>الصافي: {invoice.net_amount}</p></div>
    <p style="text-align:center;font-size:8px;">شكراً لكم</p>
    </body></html>"""
    return HttpResponse(html, content_type='text/html')


@login_required
@transaction.atomic
def create_sales_return(request):
    """مرتجع بيع"""
    if request.method == 'POST':
        sales_id = request.POST.get('sales_invoice')
        buyer_id = request.POST.get('buyer')
        items = request.POST.getlist('items[]')
        try:
            original_invoice = SalesInvoice.objects.get(id=sales_id)
            buyer = Buyer.objects.get(id=buyer_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('billing:return')

        last_return = SalesReturn.objects.order_by('-id').first()
        num = (int(last_return.invoice_number.split('-')[-1]) + 1) if last_return else 1
        invoice_number = f"SALE-RET-{num:06d}"

        return_invoice = SalesReturn.objects.create(
            invoice_number=invoice_number, sales_invoice=original_invoice,
            buyer=buyer, date=timezone.now().date(), created_by=request.user, status='APPROVED',
        )

        total = Decimal('0')
        for item_data in items:
            parts = item_data.split('|')
            product = Product.objects.get(id=parts[0])
            quantity = Decimal(parts[1])
            price = Decimal(parts[2])
            item_total = quantity * price
            SalesReturnItem.objects.create(
                return_invoice=return_invoice, product=product,
                quantity=quantity, unit_price=price, total=item_total,
            )
            total += item_total

        return_invoice.total_amount = total
        return_invoice.save()

        buyer.current_balance -= total
        buyer.total_purchases -= total
        buyer.total_remaining -= total
        buyer.save()

        messages.success(request, f'تم إنشاء مرتجع {invoice_number} بنجاح')
        return redirect('billing:list')

    return render(request, 'billing/return.html', {
        'invoices': SalesInvoice.objects.filter(status='APPROVED', is_deleted=False),
        'buyers': Buyer.objects.filter(status='ACTIVE'),
    })
