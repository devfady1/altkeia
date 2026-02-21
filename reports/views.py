from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from sessions.models import TableSession
from orders.models import Order
from activities.models import ActivitySession
from payments.models import Payment


@login_required
def reports_dashboard(request):
    if not (request.user.is_owner or request.user.is_manager):
        from django.shortcuts import redirect
        return redirect('dashboard')

    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Today stats
    today_sessions = TableSession.objects.filter(opened_at__date=today)
    today_payments = Payment.objects.filter(paid_at__date=today)
    today_orders = Order.objects.filter(created_at__date=today)

    # Monthly stats
    month_payments = Payment.objects.filter(paid_at__date__gte=month_start)
    month_sessions = TableSession.objects.filter(opened_at__date__gte=month_start)

    context = {
        'today': today,
        'today_revenue': today_payments.aggregate(total=Sum('amount'))['total'] or 0,
        'today_sessions_count': today_sessions.count(),
        'today_orders_count': today_orders.count(),
        'today_payments_count': today_payments.count(),
        'month_revenue': month_payments.aggregate(total=Sum('amount'))['total'] or 0,
        'month_sessions_count': month_sessions.count(),
        # Last 7 days revenue
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
def daily_report(request):
    if not (request.user.is_owner or request.user.is_manager):
        from django.shortcuts import redirect
        return redirect('dashboard')

    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.now().date()

    sessions = TableSession.objects.filter(
        opened_at__date=report_date, status='closed'
    ).select_related('primary_table')

    payments = Payment.objects.filter(paid_at__date=report_date)
    activities = ActivitySession.objects.filter(started_at__date=report_date, ended_at__isnull=False)

    context = {
        'report_date': report_date,
        'sessions': sessions,
        'total_revenue': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'total_discount': payments.aggregate(total=Sum('discount'))['total'] or 0,
        'sessions_count': sessions.count(),
        'activities_revenue': activities.aggregate(total=Sum('total_price'))['total'] or 0,
        'activities_count': activities.count(),
    }
    return render(request, 'reports/daily_report.html', context)


@login_required
def monthly_report(request):
    if not (request.user.is_owner or request.user.is_manager):
        from django.shortcuts import redirect
        return redirect('dashboard')

    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    month_start = today.replace(year=year, month=month, day=1)

    if month == 12:
        next_month = month_start.replace(year=year + 1, month=1)
    else:
        next_month = month_start.replace(month=month + 1)

    payments = Payment.objects.filter(paid_at__date__gte=month_start, paid_at__date__lt=next_month)
    sessions = TableSession.objects.filter(
        opened_at__date__gte=month_start, opened_at__date__lt=next_month, status='closed'
    )

    context = {
        'month': month,
        'year': year,
        'total_revenue': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'sessions_count': sessions.count(),
        'payments_count': payments.count(),
    }
    return render(request, 'reports/monthly_report.html', context)
