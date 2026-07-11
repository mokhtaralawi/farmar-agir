"""
Reports Views - التقارير
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from decimal import Decimal
from datetime import date


@login_required
def dashboard(request):
    """لوحة التحكم الرئيسية"""
    from receiving.models import ReceivingInvoice
    from billing.models import SalesInvoice
    from collectors.models import CollectionReceipt
    from payments.models import PaymentVoucher
    from partners.models import Farmer, Buyer
    from inventory.models import InventoryItem
    from cashbox.models import CashBox
    from expenses.models import Expense
    
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    context = {
        # Today's stats
        'today_receiving': ReceivingInvoice.objects.filter(date=today, status='APPROVED').aggregate(
            count=Count('id'), total=Sum('total_amount')
        ),
        'today_sales': SalesInvoice.objects.filter(date=today, status='APPROVED').aggregate(
            count=Count('id'), total=Sum('net_amount')
        ),
        'today_collections': CollectionReceipt.objects.filter(date=today).aggregate(
            count=Count('id'), total=Sum('amount')
        ),
        'today_payments': PaymentVoucher.objects.filter(date=today).aggregate(
            count=Count('id'), total=Sum('amount')
        ),
        
        # Monthly stats
        'month_receiving': ReceivingInvoice.objects.filter(
            date__gte=month_start, status='APPROVED'
        ).aggregate(count=Count('id'), total=Sum('total_amount')),
        'month_sales': SalesInvoice.objects.filter(
            date__gte=month_start, status='APPROVED'
        ).aggregate(count=Count('id'), total=Sum('net_amount')),
        
        # Summary
        'farmers_count': Farmer.objects.filter(status='ACTIVE').count(),
        'buyers_count': Buyer.objects.filter(status='ACTIVE').count(),
        'open_cashboxes': CashBox.objects.filter(status='OPEN'),
        'total_cash': sum(cb.current_balance for cb in CashBox.objects.filter(status='OPEN')),
        'low_stock': InventoryItem.objects.filter(
            remaining_qty__lte=F('product__min_stock')
        ).select_related('product')[:10],
        'pending_approvals': ReceivingInvoice.objects.filter(status='PENDING').count(),
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
def sales_report(request):
    """تقرير المبيعات"""
    from billing.models import SalesInvoice
    date_from = request.GET.get('date_from', date.today().replace(day=1).isoformat())
    date_to = request.GET.get('date_to', date.today().isoformat())
    
    invoices = SalesInvoice.objects.filter(
        date__gte=date_from, date__lte=date_to, status='APPROVED', is_deleted=False
    ).select_related('buyer')
    
    # Group by buyer
    buyers_report = {}
    for inv in invoices:
        if inv.buyer_id not in buyers_report:
            buyers_report[inv.buyer_id] = {
                'buyer': inv.buyer,
                'count': 0,
                'total': 0,
                'discount': 0,
                'net': 0,
            }
        buyers_report[inv.buyer_id]['count'] += 1
        buyers_report[inv.buyer_id]['total'] += inv.total_amount
        buyers_report[inv.buyer_id]['discount'] += inv.total_discount
        buyers_report[inv.buyer_id]['net'] += inv.net_amount
    
    totals = invoices.aggregate(
        count=Count('id'), total=Sum('total_amount'),
        discount=Sum('total_discount'), net=Sum('net_amount')
    )
    
    return render(request, 'reports/sales_report.html', {
        'invoices': invoices,
        'buyers': buyers_report.values(),
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def receiving_report(request):
    """تقرير الاستلامات"""
    from receiving.models import ReceivingInvoice
    date_from = request.GET.get('date_from', date.today().replace(day=1).isoformat())
    date_to = request.GET.get('date_to', date.today().isoformat())
    
    invoices = ReceivingInvoice.objects.filter(
        date__gte=date_from, date__lte=date_to, status='APPROVED', is_deleted=False
    ).select_related('farmer')
    
    # Group by farmer
    farmers_report = {}
    for inv in invoices:
        if inv.farmer_id not in farmers_report:
            farmers_report[inv.farmer_id] = {
                'farmer': inv.farmer,
                'count': 0,
                'total': 0,
            }
        farmers_report[inv.farmer_id]['count'] += 1
        farmers_report[inv.farmer_id]['total'] += inv.total_amount
    
    totals = invoices.aggregate(count=Count('id'), total=Sum('total_amount'))
    
    return render(request, 'reports/receiving_report.html', {
        'invoices': invoices,
        'farmers': farmers_report.values(),
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def inventory_report(request):
    """تقرير المخزون"""
    from inventory.models import InventoryItem
    from core.models import Warehouse
    
    warehouse_id = request.GET.get('warehouse')
    items = InventoryItem.objects.filter(remaining_qty__gt=0).select_related('product', 'warehouse')
    if warehouse_id:
        items = items.filter(warehouse_id=warehouse_id)
    
    totals = items.aggregate(
        total_value=Sum(F('remaining_qty') * F('avg_price'))
    )
    
    return render(request, 'reports/inventory_report.html', {
        'items': items,
        'warehouses': Warehouse.objects.filter(is_active=True),
        'totals': totals,
        'warehouse_id': warehouse_id,
    })


@login_required
def financial_report(request):
    """التقرير المالي الشامل"""
    from receiving.models import ReceivingInvoice
    from billing.models import SalesInvoice
    from collectors.models import CollectionReceipt
    from payments.models import PaymentVoucher
    from cashbox.models import CashBox
    from expenses.models import Expense
    
    date_from = request.GET.get('date_from', date.today().replace(day=1).isoformat())
    date_to = request.GET.get('date_to', date.today().isoformat())
    
    total_receiving = ReceivingInvoice.objects.filter(
        date__gte=date_from, date__lte=date_to, status='APPROVED'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    total_sales = SalesInvoice.objects.filter(
        date__gte=date_from, date__lte=date_to, status='APPROVED'
    ).aggregate(net=Sum('net_amount'))['net'] or 0
    
    total_collections = CollectionReceipt.objects.filter(
        date__gte=date_from, date__lte=date_to
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_payments = PaymentVoucher.objects.filter(
        date__gte=date_from, date__lte=date_to
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_expenses = Expense.objects.filter(
        date__gte=date_from, date__lte=date_to
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_commissions = total_sales * Decimal('0.05')  # 5% estimated
    net_profit = total_commissions - total_expenses
    
    return render(request, 'reports/financial_report.html', {
        'total_receiving': total_receiving,
        'total_sales': total_sales,
        'total_collections': total_collections,
        'total_payments': total_payments,
        'total_expenses': total_expenses,
        'total_commissions': total_commissions,
        'net_profit': net_profit,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def profit_loss(request):
    """قائمة الدخل والخسائر"""
    from expenses.models import Expense
    from accounting.models import JournalEntry
    
    date_from = request.GET.get('date_from', date.today().replace(day=1).isoformat())
    date_to = request.GET.get('date_to', date.today().isoformat())
    
    # Revenue (commissions from sales)
    from billing.models import SalesInvoice
    revenue = SalesInvoice.objects.filter(
        date__gte=date_from, date__lte=date_to, status='APPROVED'
    ).aggregate(total_discount=Sum('total_discount'))['total_discount'] or 0
    
    # Expenses
    expenses = Expense.objects.filter(
        date__gte=date_from, date__lte=date_to
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    net_profit = revenue - expenses
    
    return render(request, 'reports/profit_loss.html', {
        'revenue': revenue,
        'expenses': expenses,
        'net_profit': net_profit,
        'date_from': date_from,
        'date_to': date_to,
    })
