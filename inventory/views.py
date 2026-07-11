"""
Inventory Views - المخزون
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import InventoryItem


@login_required
def inventory_list(request):
    warehouse_id = request.GET.get('warehouse')
    items = InventoryItem.objects.filter(remaining_qty__gt=0).select_related('product', 'warehouse')
    if warehouse_id:
        items = items.filter(warehouse_id=warehouse_id)
    return render(request, 'inventory/stock.html', {'items': items})
