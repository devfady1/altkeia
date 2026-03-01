from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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

        # Get active shift
        from reports.models import CashierShift
        active_shift = CashierShift.objects.filter(is_active=True).first()
        
        shift_invoice_number = 0
        if active_shift:
            # Count payments in this shift + 1
            shift_invoice_number = Payment.objects.filter(shift=active_shift).count() + 1

        payment = Payment.objects.create(
            session=session,
            amount=session.total_amount,
            method=method,
            discount=discount,
            notes=notes,
            paid_by=request.user,
            shift=active_shift,
            shift_invoice_number=shift_invoice_number
        )
        session.close_session(user=request.user)

        # Auto-print client receipt on USB printer
        try:
            from core.printer import print_client_receipt
            print_client_receipt(payment)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error printing client receipt for payment {payment.pk}: {e}")
            # Optional: for debugging, you can print or log traceback
            import traceback
            logger.error(traceback.format_exc())

        # Redirect to dashboard directly (receipt prints from USB printer)
        return redirect('dashboard')

    return redirect('dashboard')


@login_required
@require_POST
def reprint_payment(request, pk):
    """إعادة طباعة فاتورة"""
    if not (request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)
        
    payment = get_object_or_404(Payment, pk=pk)
    try:
        from core.printer import print_client_receipt
        success = print_client_receipt(payment)
        if success:
            return JsonResponse({'success': True, 'message': 'جاري الطباعة...'})
        else:
            return JsonResponse({'error': 'فشلت الطباعة. تأكد من توصيل الطابعة.'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
