from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import TableSession
from tables.models import Table


@login_required
def session_list(request):
    sessions = TableSession.objects.filter(status__in=['open', 'active']).select_related('primary_table')
    return render(request, 'sessions/session_list.html', {'sessions': sessions})


@login_required
def open_session(request, table_id):
    table = get_object_or_404(Table, pk=table_id)
    # Check if table already has an active session
    existing = TableSession.objects.filter(
        primary_table=table,
        status__in=['open', 'active']
    ).first()
    if existing:
        return redirect('session_detail', pk=existing.pk)

    session = TableSession.objects.create(
        primary_table=table,
        opened_by=request.user,
        guest_count=request.POST.get('guest_count', 1)
    )
    session.tables.add(table)
    table.status = Table.Status.OCCUPIED
    table.save()
    return redirect('dashboard')


@login_required
def session_detail(request, pk):
    session = get_object_or_404(TableSession, pk=pk)
    session.calculate_total()
    return render(request, 'sessions/session_detail.html', {'session': session})


@login_required
def close_session(request, pk):
    if not (request.user.is_cashier or request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)
    session = get_object_or_404(TableSession, pk=pk)
    session.close_session(user=request.user)
    return redirect('dashboard')


@login_required
def merge_tables(request, pk):
    session = get_object_or_404(TableSession, pk=pk)
    if request.method == 'POST':
        table_id = request.POST.get('table_id')
        table = get_object_or_404(Table, pk=table_id)
        session.merge_table(table)
    return redirect('dashboard')
