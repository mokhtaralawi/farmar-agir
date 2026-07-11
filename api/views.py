"""
API Views - JSON API endpoints
"""

from django.http import JsonResponse
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from receiving.models import ReceivingInvoice
from billing.models import SalesInvoice
from inventory.models import InventoryItem
from partners.models import Farmer, Buyer
from cashbox.models import CashBox


@login_required
def dashboard_data(request):
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    data = {
        'today_receiving': ReceivingInvoice.objects.filter(date=today).count(),
        'today_billing': SalesInvoice.objects.filter(date=today).count(),
        'today_cashbox': Cashbox.objects.aggregate(
            total_balance=Sum('current_balance')
        ),
        'week_receiving': ReceivingInvoice.objects.filter(
            date__gte=week_ago
        ).aggregate(total=Sum('total_amount')),
        'week_billing': SalesInvoice.objects.filter(
            date__gte=week_ago
        ).aggregate(total=Sum('total_amount')),
        'total_farmers': Farmer.objects.count(),
        'total_buyers': Buyer.objects.count(),
        'total_products': InventoryItem.objects.values('product').distinct().count(),
    }
    return JsonResponse(data)


@login_required
def receiving_list(request):
    invoices = ReceivingInvoice.objects.all().order_by('-date')[:20]
    data = [{
        'id': inv.id,
        'invoice_number': inv.invoice_number,
        'farmer': inv.farmer.name,
        'total': str(inv.total_amount),
        'date': str(inv.date),
    } for inv in invoices]
    return JsonResponse(data, safe=False)


@login_required
def billing_list(request):
    invoices = SalesInvoice.objects.all().order_by('-date')[:20]
    data = [{
        'id': inv.id,
        'invoice_number': inv.invoice_number,
        'buyer': inv.buyer.name,
        'total': str(inv.total_amount),
        'date': str(inv.date),
    } for inv in invoices]
    return JsonResponse(data, safe=False)


@login_required
def inventory_data(request):
    items = InventoryItem.objects.filter(remaining_qty__gt=0).select_related('product', 'warehouse')[:20]
    data = [{
        'product': item.product.name,
        'warehouse': item.warehouse.name,
        'remaining_qty': str(item.remaining_qty),
        'unit': item.unit.name,
        'avg_price': str(item.avg_price),
    } for item in items]
    return JsonResponse(data, safe=False)


@login_required
def farmers_list(request):
    farmers = Farmer.objects.all().order_by('name')[:50]
    data = [{
        'id': f.id,
        'code': f.code,
        'name': f.name,
        'phone': f.phone,
    } for f in farmers]
    return JsonResponse(data, safe=False)


@login_required
def buyers_list(request):
    buyers = Buyer.objects.all().order_by('name')[:50]
    data = [{
        'id': b.id,
        'code': b.code,
        'name': b.name,
        'phone': b.phone,
    } for b in buyers]
    return JsonResponse(data, safe=False)
