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
    # Calculate initial total
    session.calculate_total()
    
    # Subtract any previous partial payments (e.g. from queue activities)
    from django.db.models import Sum
    previous_paid = session.payments.aggregate(Sum('amount'))['amount__sum'] or 0
    remaining_amount = session.total_amount - previous_paid

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
            amount=remaining_amount,
            method=method,
            discount=discount,
            notes=notes,
            paid_by=request.user,
            shift=active_shift,
            shift_invoice_number=shift_invoice_number
        )

        # Auto-end any running activities before closing
        for activity in session.activity_sessions.filter(ended_at__isnull=True):
            activity.end_activity()

        # Recalculate total after ending activities
        session.calculate_total()
        
        # Final amount check
        previous_paid_final = session.payments.exclude(pk=payment.pk).aggregate(Sum('amount'))['amount__sum'] or 0
        payment.amount = max(0, session.total_amount - previous_paid_final)
        payment.save()

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


@login_required
@require_POST
def cancel_payment(request, pk):
    """إلغاء فاتورة (مرتجع)"""
    if not (request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح بالإلغاء'}, status=403)
        
    payment = get_object_or_404(Payment, pk=pk)
    
    # 1. Update related TableSession total_paid if any
    session = payment.session
    if session:
        # 2. Cancel related Orders (only the ones confirmed/delivered by this payment or within this session)
        from orders.models import Order
        # Just cancel all orders in this session to void the entire receipt
        session.orders.update(status=Order.Status.CANCELLED)
        
        # 3. Handle activities if needed (maybe just let them remain, or zero their cost?)
        # For full void, we can delete the activities or just leave them since orders are the main revenue
        session.calculate_total()
        
    elif payment.activity_session:
        # Takeaway activity? Rarely used alone, but just in case
        pass
    else:
        # Takeaway explicit
        from orders.models import Order
        Order.objects.filter(shift=payment.shift, is_takeaway=True, confirmed_by=payment.paid_by, created_at__date=payment.paid_at.date()).update(status=Order.Status.CANCELLED)

    # 4. Zero out the payment to remove from shift totals, or delete it
    # We will zero it out to keep the invoice number record (as a voided record)
    payment.refunded_amount = payment.amount
    payment.amount = 0
    payment.discount = 0
    payment.notes = f"مرتجع بواسطة {request.user.username} - " + payment.notes
    payment.save()
    
    # 5. Fix Shift totals
    if payment.shift and not payment.shift.is_active:
        payment.shift.recalculate_totals()
        
    return JsonResponse({'success': True, 'message': 'تم إلغاء الفاتورة بنجاح وتحويلها لمرتجع.'})
