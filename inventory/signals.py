from django.db.models.signals import pre_save
from django.dispatch import receiver
from orders.models import Order
from decimal import Decimal


def deduct_stock_for_order(order):
    """
    خصم المواد الخام من المخزون عند تأكيد/إتمام الأوردر.
    يُستدعى يدوياً بعد إنشاء عناصر الطلب.
    """
    from inventory.models import ProductIngredient, StockTransaction
    from reports.models import CashierShift

    active_shift = CashierShift.objects.filter(is_active=True).first()

    for item in order.items.select_related('product').all():
        ingredients = ProductIngredient.objects.filter(
            product=item.product
        ).select_related('inventory_item')

        for ingredient in ingredients:
            # quantity_in_stock_unit handles unit conversion automatically
            # e.g., 200ml usage → 0.2 liter if stock is in liters
            qty_per_unit = ingredient.quantity_in_stock_unit
            total_qty = qty_per_unit * Decimal(str(item.quantity))
            inv_item = ingredient.inventory_item

            # Deduct stock
            inv_item.current_stock -= total_qty
            inv_item.save(update_fields=['current_stock'])

            # Build reason with usage unit info
            usage_unit = ingredient.get_usage_unit_display() if ingredient.usage_unit else ingredient.inventory_item.get_unit_display()
            reason = f'طلب #{order.pk} - {item.product.name} x{item.quantity} ({ingredient.quantity_used} {usage_unit}/وحدة)'

            # Record transaction
            StockTransaction.objects.create(
                inventory_item=inv_item,
                transaction_type=StockTransaction.TransactionType.OUT,
                quantity=total_qty,
                reason=reason,
                reference_order=order,
                shift=active_shift,
                created_by=order.confirmed_by,
            )


def return_stock_for_order(order):
    """إرجاع المواد الخام للمخزون عند إلغاء الأوردر"""
    from inventory.models import ProductIngredient, StockTransaction
    from reports.models import CashierShift

    active_shift = CashierShift.objects.filter(is_active=True).first()

    for item in order.items.select_related('product').all():
        ingredients = ProductIngredient.objects.filter(
            product=item.product
        ).select_related('inventory_item')

        for ingredient in ingredients:
            qty_per_unit = ingredient.quantity_in_stock_unit
            total_qty = qty_per_unit * Decimal(str(item.quantity))
            inv_item = ingredient.inventory_item

            # Return stock
            inv_item.current_stock += total_qty
            inv_item.save(update_fields=['current_stock'])

            # Record transaction
            StockTransaction.objects.create(
                inventory_item=inv_item,
                transaction_type=StockTransaction.TransactionType.IN,
                quantity=total_qty,
                reason=f'إلغاء طلب #{order.pk} - {item.product.name} x{item.quantity}',
                reference_order=order,
                shift=active_shift,
                created_by=None,
            )
