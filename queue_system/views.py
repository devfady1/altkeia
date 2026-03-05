from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import QueueEntry
from activities.models import ActivityType


@login_required
def queue_list(request):
    activity_types = ActivityType.objects.filter(is_active=True)
    waiting_queues = {}
    
    # Include ALL running activity sessions, even those without a QueueEntry
    from activities.models import ActivitySession
    active_sessions = ActivitySession.objects.filter(
        ended_at__isnull=True
    ).select_related(
        'device__activity_type', 
        'session__primary_table',
        'queue_entry'
    ).order_by('-started_at')
    
    for at in activity_types:
        waiting_queues[at] = QueueEntry.objects.filter(
            activity_type=at,
            status=QueueEntry.Status.WAITING
        ).order_by('position')
        
    from tables.models import Table
    tables = Table.objects.filter(is_active=True).order_by('floor', 'number')
    
    return render(request, 'queue_system/queue_list.html', {
        'waiting_queues': waiting_queues,
        'active_sessions': active_sessions,
        'activity_types': activity_types,
        'tables': tables
    })


@login_required
def join_queue(request):
    if request.method == 'POST':
        from tables.models import Table
        
        activity_type_id = request.POST.get('activity_type_id')
        customer_name = request.POST.get('customer_name', 'عميل')
        requested_hours = request.POST.get('requested_hours', 1)
        table_id = request.POST.get('table_id')
        device_id = request.POST.get('device_id')
        
        activity_type = get_object_or_404(ActivityType, pk=activity_type_id)
        
        last = QueueEntry.objects.filter(
            activity_type=activity_type,
            status=QueueEntry.Status.WAITING
        ).order_by('-position').first()
        position = (last.position + 1) if last else 1
        
        table = None
        if table_id:
            table = get_object_or_404(Table, pk=table_id)
            
        device = None
        if device_id:
            from activities.models import Device
            device = get_object_or_404(Device, pk=device_id)

        QueueEntry.objects.create(
            activity_type=activity_type,
            customer_name=customer_name,
            requested_hours=requested_hours,
            position=position,
            table=table,
            device=device,
            status=QueueEntry.Status.WAITING
        )
    return redirect('queue_list')


@login_required
def cancel_queue(request, pk):
    entry = get_object_or_404(QueueEntry, pk=pk)
    
    # If the entry was active, end the associated session
    if entry.status == QueueEntry.Status.ACTIVE and entry.activity_session:
        entry.activity_session.end_activity()
        if entry.session:
            entry.session.calculate_total()
            
    entry.status = QueueEntry.Status.CANCELLED
    entry.save()
    return redirect('queue_list')


@login_required
@transaction.atomic
def activate_queue(request, pk):
    # Lock the entry to prevent concurrent activation
    entry = get_object_or_404(QueueEntry.objects.select_for_update(), pk=pk)
    
    if entry.status != QueueEntry.Status.WAITING:
        return redirect('queue_list')
        
    # Find truly available device (Strict Check)
    from activities.models import Device, ActivitySession
    from django.db.models import Exists, OuterRef
    from django.contrib import messages
    
    device = None
    
    if entry.device:
        # Check if the specific requested device is free
        target_device = Device.objects.select_for_update().get(pk=entry.device.pk)
        is_busy = ActivitySession.objects.filter(device=target_device, ended_at__isnull=True).exists()
        if not is_busy:
            device = target_device
        else:
            messages.error(request, f"الجهاز {target_device.name} مشغول حالياً.")
            return redirect('queue_list')
    
    if not device:
        # Find ANY available device of the required type, locking it
        # We look for devices that have status='available' AND no active session
        available_devices = Device.objects.filter(
            activity_type=entry.activity_type,
            is_active=True
        ).select_for_update(skip_locked=True)
        
        for d in available_devices:
            if not ActivitySession.objects.filter(device=d, ended_at__isnull=True).exists():
                device = d
                break
    
    if not device:
        # No device available
        messages.error(request, f"جميع أجهزة {entry.activity_type.name} مشغولة حالياً.")
        return redirect('queue_list')
        
    # Get or create session for the table
    from sessions.models import TableSession
    from tables.models import Table
    
    table = entry.table

    if table:
        # Lock the session if it exists
        session = TableSession.objects.filter(
            primary_table=table,
            status__in=[TableSession.Status.OPEN, TableSession.Status.ACTIVE]
        ).select_for_update().first()
        
        if not session:
            session = TableSession.objects.create(primary_table=table)
            session.tables.add(table)
    else:
        # No table — create a standalone session for this activity
        session = TableSession.objects.create(primary_table=None)
        
    # Start activity
    device.status = Device.Status.BUSY
    device.save()
    
    activity_session = ActivitySession.objects.create(device=device, session=session)
    
    # Update entry
    entry.status = QueueEntry.Status.ACTIVE
    entry.activity_session = activity_session
    entry.session = session
    entry.save()
    
    # Update table status if a table is assigned
    if table:
        table.status = Table.Status.ACTIVITY
        table.save()
    
    return redirect('queue_list')


@login_required
def finish_queue_entry(request, pk):
    """Finishes an activity session. 'pk' here is the ActivitySession ID."""
    from activities.models import ActivitySession
    activity_session = get_object_or_404(ActivitySession, pk=pk)
    
    should_print = request.GET.get('print', 'false').lower() == 'true'
    
    # End the activity session
    activity_session.end_activity()
    
    # Update the table session totals
    session = activity_session.session
    session.calculate_total()
    
    # Handle associated QueueEntry if it exists
    try:
        if hasattr(activity_session, 'queue_entry'):
            entry = activity_session.queue_entry
            entry.status = QueueEntry.Status.COMPLETED
            entry.save()
    except Exception:
        pass
    
    from payments.models import Payment
    from reports.models import CashierShift
    active_shift = CashierShift.objects.filter(is_active=True).first()
    
    # If print is requested, create a payment for THIS activity specifically
    # unless a payment for this activity already exists
    payment = None
    if should_print:
        payment = Payment.objects.filter(activity_session=activity_session).first()
        if not payment:
            payment = Payment.objects.create(
                session=session,
                activity_session=activity_session,
                amount=activity_session.total_price,
                method='cash',
                paid_by=request.user,
                shift=active_shift,
                shift_invoice_number=Payment.objects.filter(shift=active_shift).count() + 1 if active_shift else 0,
            )
    
    # Print receipt if requested
    if should_print and payment:
        try:
            from core.printer import print_activity_receipt
            print_activity_receipt(activity_session)
        except Exception:
            pass
            
    return redirect('queue_list')
