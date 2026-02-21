from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Payment
from sessions.models import TableSession


@login_required
def process_payment(request, session_id):
    if not (request.user.is_cashier or request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    session = get_object_or_404(TableSession, pk=session_id)
    session.calculate_total()

    if request.method == 'POST':
        method = request.POST.get('method', 'cash')
        discount = request.POST.get('discount', 0)
        notes = request.POST.get('notes', '')

        payment = Payment.objects.create(
            session=session,
            amount=session.total_amount,
            method=method,
            discount=discount,
            notes=notes,
            paid_by=request.user
        )
        session.close_session(user=request.user)
        # Redirect to receipt page for printing
        return redirect('print_receipt', payment_id=payment.pk)

    return redirect('dashboard')


@login_required
def print_receipt(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)
    session = payment.session
    orders = session.orders.prefetch_related('items__product').all()
    activities = session.activity_sessions.select_related('device__activity_type').all()

    return render(request, 'payments/receipt.html', {
        'payment': payment,
        'session': session,
        'orders': orders,
        'activities': activities,
        'cafe_name': 'الكافيه',
    })
