"""
Inventory Services - خدمات المخزون
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import InventoryItem, InventoryMovement


class InventoryService:
    """خدمة إدارة المخزون"""

    @staticmethod
    @transaction.atomic
    def receive_product(product, warehouse, quantity, price, user, reference_type, reference_id):
        """استلام منتج وتحديث المخزون"""
        item, created = InventoryItem.objects.get_or_create(
            product=product, warehouse=warehouse,
            defaults={'received_qty': 0, 'sold_qty': 0, 'remaining_qty': 0}
        )

        item.received_qty += quantity
        item.remaining_qty += quantity
        item.last_buy_price = price

        # Update average price
        total_value = (item.received_qty * item.avg_price) if item.received_qty > 0 else 0
        item.avg_price = (total_value + (quantity * price)) / item.received_qty if item.received_qty > 0 else price

        item.save()

        movement = InventoryMovement.objects.create(
            movement_type='RECEIVED',
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            price=price,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

        return movement

    @staticmethod
    @transaction.atomic
    def sell_product(product, warehouse, quantity, price, user, reference_type, reference_id):
        """بيع منتج وتحديث المخزون"""
        try:
            item = InventoryItem.objects.get(product=product, warehouse=warehouse)
        except InventoryItem.DoesNotExist:
            raise ValueError(f"صنف {product} غير موجود في مخزن {warehouse}")

        if item.available_qty < quantity:
            raise ValueError(f"الكمية المتاحة ({item.available_qty}) أقل من المطلوبة ({quantity})")

        item.sold_qty += quantity
        item.remaining_qty -= quantity
        item.last_sell_price = price
        item.save()

        movement = InventoryMovement.objects.create(
            movement_type='SOLD',
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            price=price,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

        return movement

    @staticmethod
    @transaction.atomic
    def return_received(product, warehouse, quantity, price, user, reference_type, reference_id):
        """مرتجع استلام"""
        try:
            item = InventoryItem.objects.get(product=product, warehouse=warehouse)
        except InventoryItem.DoesNotExist:
            raise ValueError(f"صنف {product} غير موجود في مخزن {warehouse}")

        item.received_qty -= quantity
        item.remaining_qty -= quantity
        item.returned_qty += quantity
        item.save()

        movement = InventoryMovement.objects.create(
            movement_type='RETURN_IN',
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            price=price,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

        return movement

    @staticmethod
    @transaction.atomic
    def return_sold(product, warehouse, quantity, price, user, reference_type, reference_id):
        """مرتجع بيع"""
        try:
            item = InventoryItem.objects.get(product=product, warehouse=warehouse)
        except InventoryItem.DoesNotExist:
            raise ValueError(f"صنف {product} غير موجود في مخزن {warehouse}")

        item.sold_qty -= quantity
        item.remaining_qty += quantity
        item.returned_qty += quantity
        item.save()

        movement = InventoryMovement.objects.create(
            movement_type='RETURN_OUT',
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            price=price,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

        return movement

    @staticmethod
    @transaction.atomic
    def record_damage(product, warehouse, quantity, reason, user, reference_type, reference_id):
        """تسجيل تلف"""
        try:
            item = InventoryItem.objects.get(product=product, warehouse=warehouse)
        except InventoryItem.DoesNotExist:
            raise ValueError(f"صنف {product} غير موجود في مخزن {warehouse}")

        item.remaining_qty -= quantity
        item.damaged_qty += quantity
        item.save()

        movement = InventoryMovement.objects.create(
            movement_type='DAMAGED',
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

        return movement
