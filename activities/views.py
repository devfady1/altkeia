from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ActivityType, Device, ActivitySession
from sessions.models import TableSession
from tables.models import Table


@login_required
def activity_list(request):
    activity_types = ActivityType.objects.filter(is_active=True).prefetch_related('devices')
    return render(request, 'activities/activity_list.html', {'activity_types': activity_types})


@login_required
def start_activity(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        session_id = request.POST.get('session_id')
        
        from activities.models import Device, ActivityType
        from tables.models import Table
        from queue_system.models import QueueEntry
        
        device = get_object_or_404(Device, pk=device_id)
        session = get_object_or_404(TableSession, pk=session_id)
        table = session.primary_table

        # Instead of starting activity, add to queue
        last = QueueEntry.objects.filter(
            activity_type=device.activity_type,
            status=QueueEntry.Status.WAITING
        ).order_by('-position').first()
        position = (last.position + 1) if last else 1

        QueueEntry.objects.create(
            activity_type=device.activity_type,
            table=table,
            session=session,
            customer_name=table.display_name,
            position=position,
            status=QueueEntry.Status.WAITING
        )

        # Update table status to PENDING if it was EMPTY
        if table.status == Table.Status.EMPTY:
            table.status = Table.Status.PENDING
            table.save()

    return redirect('queue_list')


@login_required
def end_activity(request, pk):
    activity_session = get_object_or_404(ActivitySession, pk=pk)
    activity_session.end_activity()
    # Update session total
    activity_session.session.calculate_total()
    return redirect('dashboard')
