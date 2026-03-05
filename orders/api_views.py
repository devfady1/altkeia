from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem
from sessions.models import TableSession
from tables.models import Table
from products.models import Product, ProductSize
import json


@login_required
@require_GET
def order_list_api(request):
    orders = Order.objects.filter(
        is_from_qr=True
    ).exclude(
        status__in=['delivered', 'cancelled']
    ).select_related('table').prefetch_related('items__product', 'items__size')

    data = []
    for order in orders:
        data.append({
            'id': order.pk,
            'table': order.table.display_name,
            'status': order.status,
            'status_display': order.get_status_display(),
            'status_color': order.status_color,
            'total': float(order.total),
            'created_at': order.created_at.strftime('%H:%M'),
            'is_from_qr': order.is_from_qr,
            'items': [
                {
                    'product': item.display_name,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'subtotal': float(item.subtotal),
                    'notes': item.notes,
                }
                for item in order.items.all()
            ]
        })
    return JsonResponse({'orders': data})


@login_required
@require_POST
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    body = json.loads(request.body)
    new_status = body.get('status')

    # Role-based permissions
    user = request.user
    allowed = False
    if new_status == 'confirmed' and (user.is_waiter or user.is_manager or user.is_owner or user.is_cashier):
        allowed = True
    elif new_status == 'preparing' and (user.is_kitchen or user.is_manager or user.is_owner):
        allowed = True
    elif new_status == 'ready' and (user.is_kitchen or user.is_manager or user.is_owner):
        allowed = True
    elif new_status == 'delivered' and (user.is_waiter or user.is_cashier or user.is_manager or user.is_owner):
        allowed = True
    elif new_status == 'cancelled' and (user.is_manager or user.is_owner):
        allowed = True

    if not allowed:
        return JsonResponse({'error': 'غير مصرح بتغيير الحالة'}, status=403)

    # If cancelling an active order, return stock
    if new_status == 'cancelled' and order.status in ['confirmed', 'preparing', 'ready', 'delivered']:
        try:
            from inventory.signals import return_stock_for_order
            return_stock_for_order(order)
        except Exception:
            pass

    order.status = new_status
    
    # Auto-complete order when confirmed
    if new_status == 'confirmed':
        order.status = Order.Status.DELIVERED
        order.confirmed_by = user
        order.table.status = Table.Status.OCCUPIED
        order.table.save()

        # Assign shift order number if not set
        if not order.shift_order_number:
            from reports.models import CashierShift
            active_shift = CashierShift.objects.filter(is_active=True).first()
            if active_shift:
                order.shift = active_shift
                order.shift_order_number = Order.objects.filter(shift=active_shift).exclude(shift_order_number__isnull=True).count() + 1

    order.save()

    # Print kitchen ticket when order is confirmed
    if new_status == 'confirmed' or new_status == 'delivered':
        # Deduct inventory
        try:
            from inventory.signals import deduct_stock_for_order
            deduct_stock_for_order(order)
        except Exception:
            pass
        try:
            from core.printer import print_kitchen_receipt
            print_kitchen_receipt(order)
        except Exception:
            pass  # Don't block the response if printing fails

    return JsonResponse({
        'success': True, 
        'status': order.status, 
        'status_display': order.get_status_display(),
        'message': 'تم تأكيد وإتمام الطلب بنجاح! 🚀'
    })


@csrf_exempt
@require_POST
def create_order(request):
    """Create order - can be from QR (no auth), from staff, or takeaway"""
    body = json.loads(request.body)
    table_uuid = body.get('table_uuid')
    items = body.get('items', [])
    notes = body.get('notes', '')
    is_from_qr = body.get('is_from_qr', False)
    is_takeaway = body.get('is_takeaway', False)

    if not items:
        return JsonResponse({'error': 'بيانات ناقصة'}, status=400)

    from reports.models import CashierShift
    active_shift = CashierShift.objects.filter(is_active=True).first()

    # ===== TAKEAWAY ORDER =====
    if is_takeaway:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'يجب تسجيل الدخول'}, status=403)

        order = Order.objects.create(
            session=None,
            table=None,
            notes=notes,
            is_takeaway=True,
            status=Order.Status.DELIVERED,
            confirmed_by=request.user,
            shift=active_shift,
        )
        if active_shift:
            order.shift_order_number = Order.objects.filter(shift=active_shift).exclude(shift_order_number__isnull=True).count() + 1
            order.save()

        # Add items
        for item_data in items:
            try:
                product = Product.objects.get(pk=item_data['product_id'])
                size = None
                size_name = ''
                price = product.price
                size_id = item_data.get('size_id')
                if size_id:
                    try:
                        size = ProductSize.objects.get(pk=size_id, product=product)
                        price = size.price
                        size_name = size.display_name
                    except ProductSize.DoesNotExist:
                        pass
                OrderItem.objects.create(
                    order=order, product=product, size=size,
                    size_name=size_name, quantity=item_data.get('quantity', 1),
                    price=price, notes=item_data.get('notes', '')
                )
            except Product.DoesNotExist:
                continue

        # Deduct inventory
        try:
            from inventory.signals import deduct_stock_for_order
            deduct_stock_for_order(order)
        except Exception:
            pass
        # Print kitchen receipt
        try:
            from core.printer import print_kitchen_receipt
            print_kitchen_receipt(order)
        except Exception:
            pass

        # Auto-create payment for takeaway
        from payments.models import Payment
        total = sum(i.subtotal for i in order.items.all())
        method = body.get('method', 'cash')
        payment = Payment.objects.create(
            session=None if not hasattr(order, 'session') or not order.session else order.session,
            amount=total,
            method=method,
            paid_by=request.user,
            shift=active_shift,
            shift_invoice_number=Payment.objects.filter(shift=active_shift).count() + 1 if active_shift else 0,
        )

        # Print client receipt for takeaway
        try:
            from core.printer import print_client_receipt
            print_client_receipt(payment)
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'order_id': order.pk,
            'message': f'تم إنشاء طلب تيك أواي #{order.pk} بنجاح! 🛍️'
        })

    # ===== NORMAL TABLE ORDER =====
    if not table_uuid:
        return JsonResponse({'error': 'بيانات ناقصة'}, status=400)

    try:
        table = Table.objects.get(uuid=table_uuid)
    except Table.DoesNotExist:
        return JsonResponse({'error': 'الطاولة غير موجودة'}, status=404)

    # Get or create active session
    from django.db.models import Q
    session = TableSession.objects.filter(
        Q(tables=table) | Q(primary_table=table),
        status__in=['open', 'active']
    ).distinct().first()

    if not session:
        session = TableSession.objects.create(primary_table=table)
        session.tables.add(table)
        table.status = Table.Status.PENDING
        table.save()

    order = Order.objects.create(
        session=session,
        table=table,
        notes=notes,
        is_from_qr=is_from_qr,
        status=Order.Status.PENDING,
        shift=active_shift
    )

    # Auto-confirm if created by staff
    is_staff_order = False
    if request.user.is_authenticated and (request.user.is_waiter or request.user.is_cashier or request.user.is_manager or request.user.is_owner):
        order.status = Order.Status.DELIVERED
        order.confirmed_by = request.user
        is_staff_order = True
        if active_shift:
            order.shift_order_number = Order.objects.filter(shift=active_shift).exclude(shift_order_number__isnull=True).count() + 1
        table.status = Table.Status.OCCUPIED
        table.save()
        order.save()

    for item_data in items:
        try:
            product = Product.objects.get(pk=item_data['product_id'])
            size = None
            size_name = ''
            price = product.price
            size_id = item_data.get('size_id')
            if size_id:
                try:
                    size = ProductSize.objects.get(pk=size_id, product=product)
                    price = size.price
                    size_name = size.display_name
                except ProductSize.DoesNotExist:
                    pass
            OrderItem.objects.create(
                order=order, product=product, size=size,
                size_name=size_name, quantity=item_data.get('quantity', 1),
                price=price, notes=item_data.get('notes', '')
            )
        except Product.DoesNotExist:
            continue

    if table.status == Table.Status.EMPTY:
        table.status = Table.Status.PENDING
        table.save()

    # Trigger kitchen print and inventory deduction if auto-confirmed
    if is_staff_order:
        try:
            from inventory.signals import deduct_stock_for_order
            deduct_stock_for_order(order)
        except Exception:
            pass
        try:
            from core.printer import print_kitchen_receipt
            print_kitchen_receipt(order)
        except Exception:
            pass

    return JsonResponse({
        'success': True,
        'order_id': order.pk,
        'message': 'تم إضافة الطلب وتأكيده بنجاح! 🚀' if is_staff_order else 'تم إرسال الطلب بنجاح! سيتم تأكيده قريباً.'
    })


@login_required
@require_GET
def kitchen_orders_api(request):
    """API for kitchen - confirmed and preparing orders"""
    orders = Order.objects.filter(
        status__in=['confirmed', 'preparing']
    ).select_related('table').prefetch_related('items__product', 'items__size').order_by('created_at')

    data = []
    for order in orders:
        data.append({
            'id': order.pk,
            'table': order.table.display_name,
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at.strftime('%H:%M'),
            'items': [
                {
                    'product': item.display_name,
                    'quantity': item.quantity,
                    'notes': item.notes,
                }
                for item in order.items.all()
            ]
        })
    return JsonResponse({'orders': data})


@login_required
@require_POST
def edit_order_items_api(request, pk):
    """
    Flexibly edit an existing order:
    - Update quantities
    - Remove items
    - Add new items
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Only allow editing active/unpaid orders
    if order.status in ['cancelled']:
        return JsonResponse({'error': 'لا يمكن تعديل طلب ملغي'}, status=400)
    
    # Permissions
    user = request.user
    if not (user.is_manager or user.is_owner or user.is_waiter or user.is_cashier):
        return JsonResponse({'error': 'غير مصرح بتعديل الطلب'}, status=403)

    body = json.loads(request.body)
    items_data = body.get('items', []) # Expected list of {product_id, size_id, quantity, notes, item_id (optional)}

    # Track current item IDs to identify removals
    incoming_item_ids = [i.get('item_id') for i in items_data if i.get('item_id')]
    
    # 1. Handle Removals
    order.items.exclude(id__in=incoming_item_ids).delete()

    # 2. Update or Create Items
    for i_data in items_data:
        item_id = i_data.get('item_id')
        qty = int(i_data.get('quantity', 1))
        
        if qty <= 0:
            if item_id:
                OrderItem.objects.filter(id=item_id, order=order).delete()
            continue

        if item_id:
            # Update existing
            item = OrderItem.objects.filter(id=item_id, order=order).first()
            if item:
                item.quantity = qty
                item.notes = i_data.get('notes', item.notes)
                item.save()
        else:
            # Create new
            try:
                product = Product.objects.get(pk=i_data['product_id'])
                size = None
                size_name = ''
                price = product.price
                
                size_id = i_data.get('size_id')
                if size_id:
                    size = ProductSize.objects.filter(pk=size_id, product=product).first()
                    if size:
                        price = size.price
                        size_name = size.display_name
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    size=size,
                    size_name=size_name,
                    quantity=qty,
                    price=price,
                    notes=i_data.get('notes', '')
                )
            except (Product.DoesNotExist, KeyError):
                continue

    # 3. Recalculate session total if needed
    order.session.calculate_total()
    
    # 4. Sync payment amount if it already exists (editing a paid invoice)
    # Using the new one-to-many relationship
    last_payment = order.session.payments.order_by('-paid_at').first()
    if last_payment:
        # Re-calculate remaining if it's the final payment
        from django.db.models import Sum
        previous_paid_others = order.session.payments.exclude(pk=last_payment.pk).aggregate(total=Sum('amount'))['total'] or 0
        last_payment.amount = order.session.total_amount - previous_paid_others
        last_payment.save()

        # If shift is closed, update its cached stats
        if last_payment.shift and not last_payment.shift.is_active:
            last_payment.shift.recalculate_totals() # Recalculates all shift totals based on DB
    
    # 5. Print kitchen receipt
    try:
        from core.printer import print_kitchen_receipt
        print_kitchen_receipt(order)
    except Exception as e:
        print(f"Error printing kitchen receipt on edit: {e}")

    return JsonResponse({
        'success': True,
        'message': 'تم تحديث الطلب وطباعة تكت المطبخ! ✨',
        'total': float(order.total)
    })
