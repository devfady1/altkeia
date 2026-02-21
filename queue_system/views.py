from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import QueueEntry
from activities.models import ActivityType


@login_required
def queue_list(request):
    activity_types = ActivityType.objects.filter(is_active=True)
    queues = {}
    for at in activity_types:
        queues[at] = QueueEntry.objects.filter(
            activity_type=at,
            status='waiting'
        ).order_by('position')
    return render(request, 'queue_system/queue_list.html', {'queues': queues})


@login_required
def join_queue(request):
    if request.method == 'POST':
        activity_type = get_object_or_404(ActivityType, pk=request.POST.get('activity_type_id'))
        last = QueueEntry.objects.filter(
            activity_type=activity_type,
            status='waiting'
        ).order_by('-position').first()
        position = (last.position + 1) if last else 1

        QueueEntry.objects.create(
            activity_type=activity_type,
            customer_name=request.POST.get('customer_name', ''),
            requested_hours=request.POST.get('requested_hours', 1),
            position=position,
        )
    return redirect('queue_list')


@login_required
def cancel_queue(request, pk):
    entry = get_object_or_404(QueueEntry, pk=pk)
    entry.status = QueueEntry.Status.CANCELLED
    entry.save()
    return redirect('queue_list')


@login_required
def activate_queue(request, pk):
    entry = get_object_or_404(QueueEntry, pk=pk)
    entry.status = QueueEntry.Status.ACTIVE
    entry.save()
    return redirect('queue_list')
