from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
import json

from .models import InventoryItem, ProductIngredient, StockTransaction
from products.models import Product, Category
from reports.models import CashierShift


def _is_mgmt(user):
    """Check if user is owner or manager"""
    return user.is_owner or user.is_manager


@login_required
def inventory_dashboard(request):
    """لوحة المخزون الرئيسية"""
    if not _is_mgmt(request.user):
        return redirect('dashboard')

    items = InventoryItem.objects.filter(is_active=True)

    # Stats
    total_items = items.count()
    low_stock_count = sum(1 for i in items if i.stock_status == 'low')
    out_of_stock_count = sum(1 for i in items if i.stock_status == 'out')

    # Handle POST actions
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_item':
            InventoryItem.objects.create(
                name=request.POST.get('name'),
                unit=request.POST.get('unit', 'piece'),
                current_stock=request.POST.get('current_stock', 0),
                minimum_stock=request.POST.get('minimum_stock', 0),
                cost_per_unit=request.POST.get('cost_per_unit', 0),
            )
            return redirect('inventory_dashboard')

        elif action == 'delete_item':
            InventoryItem.objects.filter(pk=request.POST.get('id')).update(is_active=False)
            return redirect('inventory_dashboard')

        elif action == 'add_stock':
            item_id = request.POST.get('item_id')
            quantity = Decimal(request.POST.get('quantity', '0'))
            notes = request.POST.get('notes', '')

            if item_id and quantity > 0:
                inv_item = get_object_or_404(InventoryItem, pk=item_id)
                inv_item.current_stock += quantity
                inv_item.save(update_fields=['current_stock'])

                active_shift = CashierShift.objects.filter(is_active=True).first()
                StockTransaction.objects.create(
                    inventory_item=inv_item,
                    transaction_type=StockTransaction.TransactionType.IN,
                    quantity=quantity,
                    reason='إضافة وارد يدوي',
                    shift=active_shift,
                    created_by=request.user,
                    notes=notes,
                )
            return redirect('inventory_dashboard')

        elif action == 'waste':
            item_id = request.POST.get('item_id')
            quantity = Decimal(request.POST.get('quantity', '0'))
            notes = request.POST.get('notes', '')

            if item_id and quantity > 0:
                inv_item = get_object_or_404(InventoryItem, pk=item_id)
                inv_item.current_stock -= quantity
                inv_item.save(update_fields=['current_stock'])

                active_shift = CashierShift.objects.filter(is_active=True).first()
                StockTransaction.objects.create(
                    inventory_item=inv_item,
                    transaction_type=StockTransaction.TransactionType.WASTE,
                    quantity=quantity,
                    reason='هالك',
                    shift=active_shift,
                    created_by=request.user,
                    notes=notes,
                )
            return redirect('inventory_dashboard')

    context = {
        'items': items,
        'total_items': total_items,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'unit_choices': InventoryItem.Unit.choices,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def inventory_item_detail(request, item_id):
    """تفاصيل مادة خام"""
    if not _is_mgmt(request.user):
        return redirect('dashboard')

    item = get_object_or_404(InventoryItem, pk=item_id)
    transactions = item.transactions.all()[:50]
    product_usages = item.product_usages.select_related('product').all()

    # Edit item
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'edit_item':
            item.name = request.POST.get('name', item.name)
            item.unit = request.POST.get('unit', item.unit)
            item.minimum_stock = Decimal(request.POST.get('minimum_stock', str(item.minimum_stock)))
            item.cost_per_unit = Decimal(request.POST.get('cost_per_unit', str(item.cost_per_unit)))
            item.save()
            return redirect('inventory_item_detail', item_id=item.pk)

        elif action == 'adjust_stock':
            new_stock = Decimal(request.POST.get('new_stock', '0'))
            notes = request.POST.get('notes', '')
            diff = new_stock - item.current_stock

            active_shift = CashierShift.objects.filter(is_active=True).first()
            StockTransaction.objects.create(
                inventory_item=item,
                transaction_type=StockTransaction.TransactionType.ADJUSTMENT,
                quantity=abs(diff),
                reason=f'تعديل جرد: {item.current_stock} → {new_stock}',
                shift=active_shift,
                created_by=request.user,
                notes=notes,
            )
            item.current_stock = new_stock
            item.save(update_fields=['current_stock'])
            return redirect('inventory_item_detail', item_id=item.pk)

    context = {
        'item': item,
        'transactions': transactions,
        'product_usages': product_usages,
        'unit_choices': InventoryItem.Unit.choices,
    }
    return render(request, 'inventory/item_detail.html', context)


@login_required
def product_ingredients_view(request):
    """ربط المنتجات بالمواد الخام"""
    if not _is_mgmt(request.user):
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_ingredient':
            product_id = request.POST.get('product_id')
            item_id = request.POST.get('inventory_item_id')
            qty = request.POST.get('quantity_used', '0')
            usage_unit = request.POST.get('usage_unit', '')

            if product_id and item_id and Decimal(qty) > 0:
                ProductIngredient.objects.update_or_create(
                    product_id=product_id,
                    inventory_item_id=item_id,
                    defaults={
                        'quantity_used': Decimal(qty),
                        'usage_unit': usage_unit,
                    }
                )
            return redirect('product_ingredients')

        elif action == 'delete_ingredient':
            ProductIngredient.objects.filter(pk=request.POST.get('id')).delete()
            return redirect('product_ingredients')

    categories = Category.objects.prefetch_related(
        'products__ingredients__inventory_item'
    ).filter(is_active=True)
    inventory_items = InventoryItem.objects.filter(is_active=True)

    # Build product ingredients map
    products_with_ingredients = []
    for cat in categories:
        for product in cat.products.filter(is_active=True):
            ingredients = product.ingredients.select_related('inventory_item').all()
            products_with_ingredients.append({
                'product': product,
                'category': cat,
                'ingredients': ingredients,
            })

    context = {
        'products_with_ingredients': products_with_ingredients,
        'categories': categories,
        'inventory_items': inventory_items,
    }
    return render(request, 'inventory/product_ingredients.html', context)


@login_required
def shift_inventory_report(request):
    """تقرير جرد الشيفت"""
    if not _is_mgmt(request.user):
        return redirect('dashboard')

    shift_id = request.GET.get('shift_id')
    if shift_id:
        shift = get_object_or_404(CashierShift, pk=shift_id)
    else:
        shift = CashierShift.objects.filter(is_active=True).first()

    transactions = []
    summary = {}

    if shift:
        transactions = StockTransaction.objects.filter(
            shift=shift
        ).select_related('inventory_item', 'created_by', 'reference_order').order_by('-created_at')

        # Build summary per item
        for txn in transactions:
            item_name = txn.inventory_item.name
            if item_name not in summary:
                summary[item_name] = {
                    'item': txn.inventory_item,
                    'total_in': Decimal('0'),
                    'total_out': Decimal('0'),
                    'total_waste': Decimal('0'),
                    'total_adjustment': Decimal('0'),
                }
            if txn.transaction_type == 'in':
                summary[item_name]['total_in'] += txn.quantity
            elif txn.transaction_type == 'out':
                summary[item_name]['total_out'] += txn.quantity
            elif txn.transaction_type == 'waste':
                summary[item_name]['total_waste'] += txn.quantity
            elif txn.transaction_type == 'adjustment':
                summary[item_name]['total_adjustment'] += txn.quantity

    recent_shifts = CashierShift.objects.all()[:10]

    context = {
        'shift': shift,
        'transactions': transactions,
        'summary': summary.values(),
        'recent_shifts': recent_shifts,
    }
    return render(request, 'inventory/shift_report.html', context)


@login_required
def add_stock_api(request):
    """API: إضافة وارد"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if not _is_mgmt(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = Decimal(str(data.get('quantity', 0)))
        notes = data.get('notes', '')

        inv_item = get_object_or_404(InventoryItem, pk=item_id)
        inv_item.current_stock += quantity
        inv_item.save(update_fields=['current_stock'])

        active_shift = CashierShift.objects.filter(is_active=True).first()
        StockTransaction.objects.create(
            inventory_item=inv_item,
            transaction_type=StockTransaction.TransactionType.IN,
            quantity=quantity,
            reason='إضافة وارد',
            shift=active_shift,
            created_by=request.user,
            notes=notes,
        )

        return JsonResponse({
            'success': True,
            'new_stock': str(inv_item.current_stock),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
