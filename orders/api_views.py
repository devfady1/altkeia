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
    orders = Order.objects.exclude(
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
    if new_status == 'confirmed' and (user.is_waiter or user.is_manager or user.is_owner):
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

    order.status = new_status
    if new_status == 'confirmed':
        order.confirmed_by = user

    # Update table status
    if new_status == 'confirmed':
        order.table.status = Table.Status.OCCUPIED
        order.table.save()

    order.save()
    return JsonResponse({'success': True, 'status': order.status, 'status_display': order.get_status_display()})


@csrf_exempt
@require_POST
def create_order(request):
    """Create order - can be from QR (no auth) or from staff"""
    body = json.loads(request.body)
    table_uuid = body.get('table_uuid')
    items = body.get('items', [])
    notes = body.get('notes', '')
    is_from_qr = body.get('is_from_qr', False)

    if not table_uuid or not items:
        return JsonResponse({'error': 'بيانات ناقصة'}, status=400)

    try:
        table = Table.objects.get(uuid=table_uuid)
    except Table.DoesNotExist:
        return JsonResponse({'error': 'الطاولة غير موجودة'}, status=404)

    # Get or create active session
    session = TableSession.objects.filter(
        primary_table=table,
        status__in=['open', 'active']
    ).first()

    if not session:
        session = TableSession.objects.create(primary_table=table)
        session.tables.add(table)
        table.status = Table.Status.PENDING
        table.save()

    # Create order
    order = Order.objects.create(
        session=session,
        table=table,
        notes=notes,
        is_from_qr=is_from_qr,
        status=Order.Status.PENDING
    )

    for item_data in items:
        try:
            product = Product.objects.get(pk=item_data['product_id'])
            size = None
            size_name = ''
            price = product.price

            # Handle size
            size_id = item_data.get('size_id')
            if size_id:
                try:
                    size = ProductSize.objects.get(pk=size_id, product=product)
                    price = size.price
                    size_name = size.display_name
                except ProductSize.DoesNotExist:
                    pass

            OrderItem.objects.create(
                order=order,
                product=product,
                size=size,
                size_name=size_name,
                quantity=item_data.get('quantity', 1),
                price=price,
                notes=item_data.get('notes', '')
            )
        except Product.DoesNotExist:
            continue

    # Update table status
    if table.status == Table.Status.EMPTY:
        table.status = Table.Status.PENDING
        table.save()

    return JsonResponse({
        'success': True,
        'order_id': order.pk,
        'message': 'تم إرسال الطلب بنجاح! سيتم تأكيده قريباً.'
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
