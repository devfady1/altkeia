from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from core.models import Floor
from .models import Table
import json


@login_required
@require_GET
def tables_status(request):
    """Get all tables with their current status"""
    floors = Floor.objects.filter(is_active=True)
    data = []
    for floor in floors:
        tables = Table.objects.filter(floor=floor, is_active=True)
        floor_data = {
            'id': floor.pk,
            'name': floor.name,
            'tables': [
                {
                    'id': t.pk,
                    'number': t.number,
                    'name': t.display_name,
                    'status': t.status,
                    'status_display': t.get_status_display(),
                    'status_color': t.status_color,
                    'capacity': t.capacity,
                }
                for t in tables
            ]
        }
        data.append(floor_data)
    return JsonResponse({'floors': data})


@login_required
@require_POST
def update_table_status(request, pk):
    try:
        table = Table.objects.get(pk=pk)
        body = json.loads(request.body)
        table.status = body.get('status', table.status)
        table.save()
        return JsonResponse({'success': True})
    except Table.DoesNotExist:
        return JsonResponse({'error': 'الطاولة غير موجودة'}, status=404)
