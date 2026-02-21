from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import QueueEntry
from activities.models import ActivityType
import json


@require_GET
def queue_status_api(request):
    """Public API - anyone can see queue status"""
    activity_types = ActivityType.objects.filter(is_active=True)
    data = []
    for at in activity_types:
        entries = QueueEntry.objects.filter(
            activity_type=at,
            status='waiting'
        ).order_by('position')
        data.append({
            'activity_type': at.name,
            'icon': at.icon,
            'waiting_count': entries.count(),
            'entries': [
                {
                    'id': e.pk,
                    'name': e.customer_name or 'عميل',
                    'position': e.position,
                    'hours': float(e.requested_hours),
                }
                for e in entries
            ]
        })
    return JsonResponse({'queues': data})


@csrf_exempt
@require_POST
def join_queue_api(request):
    """Public API - join queue from QR"""
    body = json.loads(request.body)
    activity_type_id = body.get('activity_type_id')
    customer_name = body.get('customer_name', '')
    requested_hours = body.get('requested_hours', 1)

    activity_type = get_object_or_404(ActivityType, pk=activity_type_id)
    last = QueueEntry.objects.filter(
        activity_type=activity_type,
        status='waiting'
    ).order_by('-position').first()
    position = (last.position + 1) if last else 1

    entry = QueueEntry.objects.create(
        activity_type=activity_type,
        customer_name=customer_name,
        requested_hours=requested_hours,
        position=position,
    )

    return JsonResponse({
        'success': True,
        'position': entry.position,
        'waiting_before': entry.waiting_count,
        'message': f'تم تسجيلك في الطابور. ترتيبك: {entry.position}'
    })


@csrf_exempt
@require_POST
def cancel_queue_api(request, pk):
    entry = get_object_or_404(QueueEntry, pk=pk)
    entry.status = QueueEntry.Status.CANCELLED
    entry.save()
    return JsonResponse({'success': True})
