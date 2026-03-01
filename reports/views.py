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

    # Current month stats from shifts
    today = timezone.now().date()
    month_start = today.replace(day=1)
    month_shifts = CashierShift.objects.filter(
        started_at__date__gte=month_start,
        is_active=False
    )
    month_revenue = month_shifts.aggregate(total=Sum('total_revenue'))['total'] or 0
    month_orders = month_shifts.aggregate(total=Sum('total_orders'))['total'] or 0

    # Active shift stats (live)
    active_revenue = 0
    active_orders = 0
    active_sessions = 0
    if active_shift:
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

    # Sessions during this shift
    end_time = shift.ended_at or timezone.now()
    sessions = TableSession.objects.filter(
        opened_at__gte=shift.started_at,
        opened_at__lte=end_time,
        status='closed'
    ).select_related('primary_table')

    payments = Payment.objects.filter(
        paid_at__gte=shift.started_at,
        paid_at__lte=end_time
    )

    activities = ActivitySession.objects.filter(
        started_at__gte=shift.started_at,
        started_at__lte=end_time,
        ended_at__isnull=False
    )

    orders = Order.objects.filter(
        created_at__gte=shift.started_at,
        created_at__lte=end_time
    ).exclude(status=Order.Status.CANCELLED)

    # Staff deductions during this shift
    staff_orders = StaffOrder.objects.filter(
        created_at__gte=shift.started_at,
        created_at__lte=end_time
    ).select_related('employee', 'created_by')
    staff_advances = StaffAdvance.objects.filter(
        created_at__gte=shift.started_at,
        created_at__lte=end_time
    ).select_related('employee', 'created_by')
    staff_orders_total = staff_orders.aggregate(total=Sum('amount'))['total'] or 0
    staff_advances_total = staff_advances.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'shift': shift,
        'sessions': sessions,
        'total_revenue': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'total_discount': payments.aggregate(total=Sum('discount'))['total'] or 0,
        'sessions_count': sessions.count(),
        'orders_count': orders.count(),
        'activities_revenue': activities.aggregate(total=Sum('total_price'))['total'] or 0,
        'activities_count': activities.count(),
        'staff_orders': staff_orders,
        'staff_advances': staff_advances,
        'staff_orders_total': staff_orders_total,
        'staff_advances_total': staff_advances_total,
        'staff_deductions_total': staff_orders_total + staff_advances_total,
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

    context = {
        'month': month,
        'year': year,
        'shifts': shifts,
        'total_revenue': shifts.aggregate(total=Sum('total_revenue'))['total'] or 0,
        'total_orders': shifts.aggregate(total=Sum('total_orders'))['total'] or 0,
        'total_sessions': shifts.aggregate(total=Sum('total_sessions'))['total'] or 0,
        'total_discount': shifts.aggregate(total=Sum('total_discount'))['total'] or 0,
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
    
    if shift_id:
        selected_shift = get_object_or_404(CashierShift, pk=shift_id)
        payments = Payment.objects.filter(shift=selected_shift).select_related('session__primary_table', 'paid_by')
    else:
        # Default to active shift or most recent
        selected_shift = active_shift or CashierShift.objects.order_by('-started_at').first()
        if selected_shift:
            payments = Payment.objects.filter(shift=selected_shift).select_related('session__primary_table', 'paid_by')
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

    shift = CashierShift.objects.create(started_by=request.user)
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
