from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import ActivityType, Device, ActivitySession
from sessions.models import TableSession
from tables.models import Table
import json


@login_required
@require_POST
def start_activity_api(request):
    body = json.loads(request.body)
    device_id = body.get('device_id')
    session_id = body.get('session_id')
    device = get_object_or_404(Device, pk=device_id)
    session = get_object_or_404(TableSession, pk=session_id)

    if device.status != Device.Status.AVAILABLE:
        return JsonResponse({'error': 'الجهاز غير متاح'}, status=400)

    device.status = Device.Status.BUSY
    device.save()

    act = ActivitySession.objects.create(device=device, session=session)
    session.primary_table.status = Table.Status.ACTIVITY
    session.primary_table.save()

    return JsonResponse({'success': True, 'activity_id': act.pk})


@login_required
@require_POST
def end_activity_api(request, pk):
    act = get_object_or_404(ActivitySession, pk=pk)
    act.end_activity()
    act.session.calculate_total()
    return JsonResponse({
        'success': True,
        'total_price': float(act.total_price),
        'duration': act.duration_display,
    })


@login_required
@require_GET
def devices_status_api(request):
    activity_types = ActivityType.objects.filter(is_active=True)
    data = []
    for at in activity_types:
        devices = at.devices.filter(is_active=True)
        data.append({
            'id': at.pk,
            'name': at.name,
            'icon': at.icon,
            'price_per_hour': float(at.price_per_hour),
            'devices': [
                {
                    'id': d.pk,
                    'name': d.name,
                    'status': d.status,
                    'status_display': d.get_status_display(),
                }
                for d in devices
            ]
        })
    return JsonResponse({'activity_types': data})
