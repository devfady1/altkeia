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
            'created_at': order.created_at.strftime('%H:%M'),
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
        'opened_at': session.opened_at.strftime('%H:%M'),
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
    table = get_object_or_404(Table, pk=table_id)
    session = TableSession.objects.filter(
        tables=table,
        status__in=['open', 'active']
    ).first()
    if not session:
        return JsonResponse({'error': 'لا توجد جلسة نشطة'}, status=404)

    session.calculate_total()
    orders_data = []
    for order in session.orders.all():
        orders_data.append({
            'id': order.pk,
            'status': order.status,
            'status_display': order.get_status_display(),
            'status_color': order.status_color,
            'total': float(order.total),
            'created_at': order.created_at.strftime('%H:%M'),
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
        'opened_at': session.opened_at.strftime('%H:%M'),
        'notes': session.notes,
    })
