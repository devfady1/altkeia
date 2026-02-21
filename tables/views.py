from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import Floor
from tables.models import Table


@login_required
def dashboard(request):
    floors = Floor.objects.filter(is_active=True).prefetch_related('tables')
    context = {
        'floors': floors,
        'status_choices': Table.Status.choices,
    }
    return render(request, 'tables/dashboard.html', context)
