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
        device = get_object_or_404(Device, pk=device_id)
        session = get_object_or_404(TableSession, pk=session_id)

        device.status = Device.Status.BUSY
        device.save()

        ActivitySession.objects.create(device=device, session=session)

        # Update table status
        session.primary_table.status = Table.Status.ACTIVITY
        session.primary_table.save()

    return redirect('dashboard')


@login_required
def end_activity(request, pk):
    activity_session = get_object_or_404(ActivitySession, pk=pk)
    activity_session.end_activity()
    # Update session total
    activity_session.session.calculate_total()
    return redirect('dashboard')
