from django.shortcuts import render, get_object_or_404
from tables.models import Table
from products.models import Category
from sessions.models import TableSession
from activities.models import ActivityType
from queue_system.models import QueueEntry


def qr_menu(request, table_uuid):
    """QR Menu - no login required"""
    table = get_object_or_404(Table, uuid=table_uuid)
    categories = Category.objects.filter(is_active=True).prefetch_related(
        'products'
    )
    # Get active session for this table
    session = TableSession.objects.filter(
        primary_table=table,
        status__in=['open', 'active']
    ).first()

    # Activity types for queue
    activity_types = ActivityType.objects.filter(is_active=True)
    queue_data = []
    for at in activity_types:
        waiting = QueueEntry.objects.filter(activity_type=at, status='waiting').count()
        queue_data.append({
            'id': at.pk,
            'name': at.name,
            'icon': at.icon,
            'price_per_hour': at.price_per_hour,
            'waiting_count': waiting,
        })

    context = {
        'table': table,
        'categories': categories,
        'session': session,
        'activity_types': queue_data,
    }
    return render(request, 'qr_menu/menu.html', context)


def qr_bill(request, table_uuid):
    """Live bill view - no login required"""
    table = get_object_or_404(Table, uuid=table_uuid)
    session = TableSession.objects.filter(
        primary_table=table,
        status__in=['open', 'active']
    ).first()

    if session:
        session.calculate_total()

    context = {
        'table': table,
        'session': session,
    }
    return render(request, 'qr_menu/bill.html', context)
