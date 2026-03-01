from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import TableSession
from tables.models import Table
import json


@login_required
@require_GET
def session_detail_api(request, pk):
    session = get_object_or_404(TableSession, pk=pk)
    session.calculate_total()
    orders_data = []
    for order in session.orders.all():
        orders_data.append({
            'id': order.pk,
            'status': order.status,
            'status_display': order.get_status_display(),
            'status_color': order.status_color,
            'total': float(order.total),
            'created_at': order.created_at.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م'),
            'items': [
                {
                    'product': item.product.name,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'subtotal': float(item.subtotal),
                    'notes': item.notes,
                }
                for item in order.items.select_related('product').all()
            ]
        })

    activities_data = []
    for act in session.activity_sessions.select_related('device', 'device__activity_type').all():
        activities_data.append({
            'id': act.pk,
            'device': act.device.name,
            'type': act.device.activity_type.name,
            'duration': act.duration_display,
            'cost': float(act.running_cost),
            'ended': act.ended_at is not None,
        })

    return JsonResponse({
        'id': session.pk,
        'tables': [
            {'id': t.pk, 'name': t.display_name}
            for t in session.tables.all()
        ],
        'status': session.status,
        'status_display': session.get_status_display(),
        'duration': session.duration,
        'guest_count': session.guest_count,
        'total_orders': float(session.total_orders),
        'total_activities': float(session.total_activities),
        'total_amount': float(session.total_amount),
        'orders': orders_data,
        'activities': activities_data,
        'opened_at': session.opened_at.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م'),
        'notes': session.notes,
    })


@login_required
@require_POST
def close_session_api(request, pk):
    if not (request.user.is_cashier or request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)
    session = get_object_or_404(TableSession, pk=pk)
    session.close_session(user=request.user)
    return JsonResponse({'success': True})


@login_required
@require_POST
def merge_tables_api(request, pk):
    session = get_object_or_404(TableSession, pk=pk)
    body = json.loads(request.body)
    table_id = body.get('table_id')
    table = get_object_or_404(Table, pk=table_id)
    session.merge_table(table)
    return JsonResponse({'success': True})


@login_required
@require_GET
def session_by_table_api(request, table_id):
    """Find active session for a table and return full details"""
    from django.db.models import Q
    table = get_object_or_404(Table, pk=table_id)
    
    # Check both primary_table and M2M tables
    session = TableSession.objects.filter(
        Q(tables=table) | Q(primary_table=table),
        status__in=['open', 'active']
    ).distinct().first()

    if not session:
        return JsonResponse({
            'error': 'لا توجد جلسة نشطة لهذه الطاولة',
            'table_id': table_id,
            'table_status': table.status
        }, status=404)

    session.calculate_total()
    orders_data = []
    for order in session.orders.all():
        orders_data.append({
            'id': order.pk,
            'status': order.status,
            'status_display': order.get_status_display(),
            'status_color': order.status_color,
            'total': float(order.total),
            'created_at': order.created_at.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م'),
            'items': [
                {
                    'product': item.product.name,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'subtotal': float(item.subtotal),
                    'notes': item.notes,
                }
                for item in order.items.select_related('product').all()
            ]
        })

    activities_data = []
    for act in session.activity_sessions.select_related('device', 'device__activity_type').all():
        activities_data.append({
            'id': act.pk,
            'device': act.device.name,
            'type': act.device.activity_type.name,
            'duration': act.duration_display,
            'cost': float(act.running_cost),
            'ended': act.ended_at is not None,
        })

    return JsonResponse({
        'id': session.pk,
        'tables': [
            {'id': t.pk, 'name': t.display_name}
            for t in session.tables.all()
        ],
        'status': session.status,
        'status_display': session.get_status_display(),
        'duration': session.duration,
        'guest_count': session.guest_count,
        'total_orders': float(session.total_orders),
        'total_activities': float(session.total_activities),
        'total_amount': float(session.total_amount),
        'orders': orders_data,
        'activities': activities_data,
        'opened_at': session.opened_at.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م'),
        'notes': session.notes,
    })


@login_required
@require_POST
def open_session_api(request):
    try:
        body = json.loads(request.body)
        table_id = body.get('table_id')
        guest_count = body.get('guest_count', 1)
        
        table = get_object_or_404(Table, pk=table_id)
        
        # Check if table is already occupied
        if TableSession.objects.filter(tables=table, status__in=['open', 'active']).exists():
            return JsonResponse({'error': 'الطاولة مشغولة بالفعل'}, status=400)
            
        session = TableSession.objects.create(
            primary_table=table,
            guest_count=guest_count,
            opened_by=request.user
        )
        session.tables.add(table)
        
        table.status = Table.Status.OCCUPIED
        table.save()
        
        return JsonResponse({'success': True, 'session_id': session.pk})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def edit_session_items_api(request, pk):
    """
    Flexibly edit all items in a session:
    - Update quantities
    - Remove items
    - Adds are not fully supported via this endpoint yet but could be
    """
    session = get_object_or_404(TableSession, pk=pk)
    
    # Permissions
    user = request.user
    if not (user.is_manager or user.is_owner or user.is_waiter or user.is_cashier):
        return JsonResponse({'error': 'غير مصرح بتعديل الجلسة'}, status=403)

    from orders.models import OrderItem, Order
    from products.models import Product, ProductSize

    body = json.loads(request.body)
    items_data = body.get('items', [])
    
    # Get all current item IDs in the session
    current_item_ids = list(OrderItem.objects.filter(order__session=session).values_list('id', flat=True))
    incoming_item_ids = [i.get('item_id') for i in items_data if i.get('item_id')]
    
    # Removals
    to_delete = set(current_item_ids) - set(incoming_item_ids)
    if to_delete:
        OrderItem.objects.filter(id__in=to_delete, order__session=session).delete()

    # Get a default order to attach new items to
    default_order = session.orders.exclude(status=Order.Status.CANCELLED).first()
    if not default_order and items_data:
        from reports.models import CashierShift
        active_shift = CashierShift.objects.filter(is_active=True).first()
        default_order = Order.objects.create(
            session=session,
            table=session.primary_table,
            status=Order.Status.DELIVERED,
            shift=active_shift,
            confirmed_by=user
        )

    # Add/Update
    for i_data in items_data:
        item_id = i_data.get('item_id')
        qty = int(i_data.get('quantity', 1))
        
        if qty <= 0:
            if item_id:
                OrderItem.objects.filter(id=item_id, order__session=session).delete()
            continue

        if item_id:
            item = OrderItem.objects.filter(id=item_id, order__session=session).first()
            if item:
                item.quantity = qty
                item.notes = i_data.get('notes', item.notes)
                item.save()
        else:
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
                    order=default_order,
                    product=product,
                    size=size,
                    size_name=size_name,
                    quantity=qty,
                    price=price,
                    notes=i_data.get('notes', '')
                )
            except (Product.DoesNotExist, KeyError):
                continue

    session.calculate_total()
    
    if hasattr(session, 'payment'):
        payment = session.payment
        payment.amount = session.total_amount
        payment.save()
        if payment.shift and not payment.shift.is_active:
            payment.shift.recalculate_totals()
            
    return JsonResponse({'success': True, 'message': 'تم تحديث الفاتورة بنجاح! ✨'})
