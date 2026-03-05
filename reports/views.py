from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta
from sessions.models import TableSession
from orders.models import Order
from activities.models import ActivitySession
from payments.models import Payment
from accounts.models import StaffOrder, StaffAdvance
from .models import CashierShift


@login_required
def reports_dashboard(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')

    # Recent shifts
    recent_shifts = CashierShift.objects.all()[:10]
    active_shift = CashierShift.objects.filter(is_active=True).first()

    # Current month stats from ALL payments/orders, not just closed shifts
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Revenue is sum of all payments in the month
    month_payments = Payment.objects.filter(paid_at__date__gte=month_start)
    month_revenue = month_payments.aggregate(total=Sum('amount'))['total'] or 0
    
    # Orders are sum of all confirmed/completed orders in the month
    month_orders_qs = Order.objects.filter(created_at__date__gte=month_start).exclude(status=Order.Status.CANCELLED)
    month_orders = month_orders_qs.count()
    
    month_shifts = CashierShift.objects.filter(started_at__date__gte=month_start, is_active=False)

    # Active shift stats (live)
    active_revenue = 0
    active_orders = 0
    active_sessions = 0
    if active_shift:
        # Include all payments during this shift's timeframe, even unassigned ones
        active_payments = Payment.objects.filter(paid_at__gte=active_shift.started_at)
        active_revenue = active_payments.aggregate(total=Sum('amount'))['total'] or 0
        active_orders = Order.objects.filter(
            created_at__gte=active_shift.started_at
        ).exclude(status=Order.Status.CANCELLED).count()
        active_sessions = TableSession.objects.filter(
            opened_at__gte=active_shift.started_at
        ).count()

    context = {
        'today': today,
        'recent_shifts': recent_shifts,
        'active_shift': active_shift,
        'active_revenue': active_revenue,
        'active_orders': active_orders,
        'active_sessions': active_sessions,
        'month_revenue': month_revenue,
        'month_orders': month_orders,
        'month_shifts_count': month_shifts.count(),
        'week_data': _get_week_data(today),
    }
    return render(request, 'reports/dashboard.html', context)


def _get_week_data(today):
    data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        revenue = Payment.objects.filter(
            paid_at__date=day
        ).aggregate(total=Sum('amount'))['total'] or 0
        sessions_count = TableSession.objects.filter(
            opened_at__date=day
        ).count()
        data.append({
            'date': day.strftime('%m/%d'),
            'day_name': ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'][day.weekday()],
            'revenue': float(revenue),
            'sessions': sessions_count,
        })
    return data


@login_required
def shift_report(request, pk):
    if not (request.user.is_owner or request.user.is_manager or request.user.is_cashier):
        return redirect('dashboard')

    shift = get_object_or_404(CashierShift, pk=pk)

    end_time = shift.ended_at or timezone.now()
    
    # To include items without a shift, we find the end time of the *previous* shift.
    # Any item without a shift created between previous shift end and this shift end belongs to this report.
    prev_shift = CashierShift.objects.filter(started_at__lt=shift.started_at).order_by('-started_at').first()
    start_time = prev_shift.ended_at if prev_shift and prev_shift.ended_at else shift.started_at

    from django.db.models import Q
    
    # Items belong to this shift if they were opened between start and end
    # Note: TableSession doesn't have a 'shift' field, so we filter by opened_at
    sessions = TableSession.objects.filter(
        opened_at__gte=start_time, 
        opened_at__lte=end_time,
        status='closed'
    ).select_related('primary_table')

    pay_filter = Q(shift=shift) | (Q(shift__isnull=True) & Q(paid_at__gte=start_time, paid_at__lte=end_time))
    payments = Payment.objects.filter(pay_filter)

    # Filter activities by started_at within the shift timeframe
    activities = ActivitySession.objects.filter(
        started_at__gte=start_time, 
        started_at__lte=end_time,
        ended_at__isnull=False
    )

    ord_filter = Q(shift=shift) | (Q(shift__isnull=True) & Q(created_at__gte=start_time, created_at__lte=end_time))
    orders = Order.objects.filter(ord_filter).exclude(status=Order.Status.CANCELLED)
    
    # We can pass out-of-shift payments specifically to the template if the user wants to see them
    unassigned_payments = payments.filter(shift__isnull=True).select_related('paid_by')

    staff_filter = Q(shift=shift) | (Q(shift__isnull=True) & Q(created_at__gte=start_time, created_at__lte=end_time))
    staff_orders = StaffOrder.objects.filter(staff_filter).select_related('employee', 'created_by')
    staff_advances = StaffAdvance.objects.filter(staff_filter).select_related('employee', 'created_by')
    
    staff_orders_total = staff_orders.aggregate(total=Sum('amount'))['total'] or 0
    staff_advances_total = staff_advances.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'shift': shift,
        'sessions': sessions,
        'total_revenue': round(float(payments.aggregate(total=Sum('amount'))['total'] or 0), 2),
        'total_discount': round(float(payments.aggregate(total=Sum('discount'))['total'] or 0), 2),
        'sessions_count': sessions.count(),
        'orders_count': orders.count(),
        'activities_revenue': round(float(activities.aggregate(total=Sum('total_price'))['total'] or 0), 2),
        'activities_count': activities.count(),
        'staff_orders': staff_orders,
        'staff_advances': staff_advances,
        'staff_orders_total': round(float(staff_orders_total), 2),
        'staff_advances_total': round(float(staff_advances_total), 2),
        'staff_deductions_total': round(float(staff_orders_total + staff_advances_total), 2),
        'unassigned_payments': unassigned_payments,
    }
    return render(request, 'reports/shift_report.html', context)


@login_required
def monthly_report(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')

    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    month_start = today.replace(year=year, month=month, day=1)

    if month == 12:
        next_month = month_start.replace(year=year + 1, month=1)
    else:
        next_month = month_start.replace(month=month + 1)

    # Get all shifts in this month
    shifts = CashierShift.objects.filter(
        started_at__date__gte=month_start,
        started_at__date__lt=next_month,
        is_active=False
    )

    # Revenue and Orders from all records in this month (not just from shifts)
    month_payments = Payment.objects.filter(paid_at__gte=month_start, paid_at__lt=next_month)
    total_revenue = month_payments.aggregate(total=Sum('amount'))['total'] or 0
    total_discount = month_payments.aggregate(total=Sum('discount'))['total'] or 0
    total_orders = Order.objects.filter(created_at__gte=month_start, created_at__lt=next_month).exclude(status=Order.Status.CANCELLED).count()

    context = {
        'month': month,
        'year': year,
        'shifts': shifts,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_sessions': shifts.aggregate(total=Sum('total_sessions'))['total'] or 0,
        'total_discount': total_discount,
        'shifts_count': shifts.count(),
    }
    return render(request, 'reports/monthly_report.html', context)
    
@login_required
def invoice_list(request):
    """قائمة مراجعة الفواتير"""
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
        
    shift_id = request.GET.get('shift_id')
    active_shift = CashierShift.objects.filter(is_active=True).first()
    
    if shift_id == 'none':
        selected_shift = None
        payments = Payment.objects.filter(shift__isnull=True).select_related('session__primary_table', 'paid_by').order_by('-paid_at')
    elif shift_id:
        selected_shift = get_object_or_404(CashierShift, pk=shift_id)
        payments = Payment.objects.filter(shift=selected_shift).select_related('session__primary_table', 'paid_by').order_by('-paid_at')
    else:
        # Default to active shift or most recent
        selected_shift = active_shift or CashierShift.objects.order_by('-started_at').first()
        if selected_shift:
            payments = Payment.objects.filter(shift=selected_shift).select_related('session__primary_table', 'paid_by').order_by('-paid_at')
        else:
            payments = Payment.objects.none()
            
    recent_shifts = CashierShift.objects.all()[:20]
    
    context = {
        'payments': payments,
        'selected_shift': selected_shift,
        'active_shift': active_shift,
        'recent_shifts': recent_shifts,
    }
    return render(request, 'reports/invoice_list.html', context)


# ===== Shift API Endpoints =====

@login_required
@require_POST
def start_shift(request):
    """بدء شيفت جديد"""
    if not (request.user.is_cashier or request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    # Check if there's already an active shift
    existing = CashierShift.objects.filter(is_active=True).first()
    if existing:
        return JsonResponse({
            'error': 'يوجد شيفت مفتوح بالفعل',
            'shift_id': existing.pk,
            'started_by': str(existing.started_by),
        }, status=400)

    import json
    body = json.loads(request.body) if request.body else {}
    s_type = body.get('shift_type', CashierShift.ShiftType.MORNING)
    
    shift = CashierShift.objects.create(started_by=request.user, shift_type=s_type)
    # 12-hour format for response
    started_at_str = shift.started_at.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م')
    return JsonResponse({
        'success': True,
        'shift_id': shift.pk,
        'started_at': started_at_str,
        'message': 'تم بدء الشيفت بنجاح ✅'
    })


@login_required
@require_POST
def end_shift(request):
    """إنهاء الشيفت الحالي"""
    if not (request.user.is_cashier or request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    shift = CashierShift.objects.filter(is_active=True).first()
    if not shift:
        return JsonResponse({'error': 'لا يوجد شيفت مفتوح'}, status=400)

    shift.close_shift(user=request.user)
    return JsonResponse({
        'success': True,
        'shift_id': shift.pk,
        'total_revenue': float(shift.total_revenue),
        'total_orders': shift.total_orders,
        'total_sessions': shift.total_sessions,
        'total_discount': float(shift.total_discount),
        'duration': shift.duration,
        'message': 'تم إنهاء الشيفت بنجاح ✅'
    })


@login_required
def shift_status(request):
    """حالة الشيفت الحالي (JSON API)"""
    shift = CashierShift.objects.filter(is_active=True).first()
    if not shift:
        return JsonResponse({'active': False})

    # Live stats
    active_payments = Payment.objects.filter(paid_at__gte=shift.started_at)
    active_revenue = active_payments.aggregate(total=Sum('amount'))['total'] or 0
    active_orders = Order.objects.filter(
        created_at__gte=shift.started_at
    ).exclude(status=Order.Status.CANCELLED).count()

    return JsonResponse({
        'active': True,
        'shift_id': shift.pk,
        'started_by': str(shift.started_by),
        'started_at': shift.started_at.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م'),
        'duration_seconds': shift.duration_seconds,
        'duration': shift.duration,
        'revenue': float(active_revenue),
        'orders': active_orders,
    })

@login_required
@require_POST
def print_shift_report_api(request, pk):
    """طباعة تقرير الشيفت (4 ريسيت)"""
    if not (request.user.is_owner or request.user.is_manager or request.user.is_cashier):
        return JsonResponse({'error': 'غير مصرح'}, status=403)
        
    try:
        from core.printer import print_shift_report
        success = print_shift_report(shift_id=pk, printed_by=request.user)
        if success:
            return JsonResponse({'success': True, 'message': 'جاري طباعة تقرير الشيفت...'})
        else:
            return JsonResponse({'error': 'فشلت الطباعة. تأكد من توصيل الطابعة.'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

