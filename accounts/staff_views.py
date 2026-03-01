from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum
from .models import User, StaffOrder, StaffAdvance
from reports.models import CashierShift


@login_required
def employee_detail(request, pk):
    """صفحة تفاصيل الموظف"""
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')

    employee = get_object_or_404(User, pk=pk)

    # Current shift
    active_shift = CashierShift.objects.filter(is_active=True).first()

    # Shift filter
    shift_id = request.GET.get('shift_id')
    selected_shift = None
    if shift_id:
        selected_shift = get_object_or_404(CashierShift, pk=shift_id)
    elif active_shift:
        selected_shift = active_shift

    # Monthly filter
    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    # Shift data
    shift_orders = StaffOrder.objects.none()
    shift_advances = StaffAdvance.objects.none()
    shift_orders_total = 0
    shift_advances_total = 0

    if selected_shift:
        end_time = selected_shift.ended_at or timezone.now()
        shift_orders = StaffOrder.objects.filter(
            employee=employee,
            created_at__gte=selected_shift.started_at,
            created_at__lte=end_time
        )
        shift_advances = StaffAdvance.objects.filter(
            employee=employee,
            created_at__gte=selected_shift.started_at,
            created_at__lte=end_time
        )
        shift_orders_total = shift_orders.aggregate(t=Sum('amount'))['t'] or 0
        shift_advances_total = shift_advances.aggregate(t=Sum('amount'))['t'] or 0

    # Monthly data
    month_start = today.replace(year=year, month=month, day=1)
    if month == 12:
        next_month = month_start.replace(year=year + 1, month=1)
    else:
        next_month = month_start.replace(month=month + 1)

    monthly_orders = StaffOrder.objects.filter(
        employee=employee,
        created_at__date__gte=month_start,
        created_at__date__lt=next_month
    )
    monthly_advances = StaffAdvance.objects.filter(
        employee=employee,
        created_at__date__gte=month_start,
        created_at__date__lt=next_month
    )
    monthly_orders_total = monthly_orders.aggregate(t=Sum('amount'))['t'] or 0
    monthly_advances_total = monthly_advances.aggregate(t=Sum('amount'))['t'] or 0
    total_deductions = monthly_orders_total + monthly_advances_total
    net_salary = employee.salary - total_deductions

    # Recent shifts for selector
    recent_shifts = CashierShift.objects.all()[:20]

    # All employees for quick nav
    employees = User.objects.filter(is_active_employee=True).order_by('first_name')

    context = {
        'employee': employee,
        'active_shift': active_shift,
        'selected_shift': selected_shift,
        'recent_shifts': recent_shifts,
        'employees': employees,
        # Shift data
        'shift_orders': shift_orders,
        'shift_advances': shift_advances,
        'shift_orders_total': shift_orders_total,
        'shift_advances_total': shift_advances_total,
        'shift_deductions_total': shift_orders_total + shift_advances_total,
        # Monthly data
        'month': month,
        'year': year,
        'monthly_orders': monthly_orders,
        'monthly_advances': monthly_advances,
        'monthly_orders_total': monthly_orders_total,
        'monthly_advances_total': monthly_advances_total,
        'total_deductions': total_deductions,
        'net_salary': net_salary,
    }
    return render(request, 'core/employee_detail.html', context)


@login_required
@require_POST
def add_staff_order(request):
    """إضافة طلب موظف"""
    if not (request.user.is_owner or request.user.is_manager or request.user.is_cashier):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    employee_id = request.POST.get('employee_id')
    description = request.POST.get('description', '')
    amount = request.POST.get('amount', 0)

    if not employee_id or not amount:
        return JsonResponse({'error': 'بيانات ناقصة'}, status=400)

    employee = get_object_or_404(User, pk=employee_id)
    active_shift = CashierShift.objects.filter(is_active=True).first()

    order = StaffOrder.objects.create(
        employee=employee,
        description=description,
        amount=amount,
        shift=active_shift,
        created_by=request.user
    )

    return JsonResponse({
        'success': True,
        'id': order.pk,
        'message': f'تم إضافة طلب لـ {employee.get_full_name() or employee.username} ✅'
    })


@login_required
@require_POST
def add_staff_advance(request):
    """إضافة سلفة"""
    if not (request.user.is_owner or request.user.is_manager or request.user.is_cashier):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    employee_id = request.POST.get('employee_id')
    amount = request.POST.get('amount', 0)
    reason = request.POST.get('reason', '')

    if not employee_id or not amount:
        return JsonResponse({'error': 'بيانات ناقصة'}, status=400)

    employee = get_object_or_404(User, pk=employee_id)
    active_shift = CashierShift.objects.filter(is_active=True).first()

    advance = StaffAdvance.objects.create(
        employee=employee,
        amount=amount,
        reason=reason,
        shift=active_shift,
        created_by=request.user
    )

    return JsonResponse({
        'success': True,
        'id': advance.pk,
        'message': f'تم إضافة سلفة لـ {employee.get_full_name() or employee.username} ✅'
    })


@login_required
@require_POST
def delete_staff_order(request, pk):
    """حذف طلب موظف"""
    if not (request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    order = get_object_or_404(StaffOrder, pk=pk)
    order.delete()
    return JsonResponse({'success': True, 'message': 'تم الحذف ✅'})


@login_required
@require_POST
def delete_staff_advance(request, pk):
    """حذف سلفة"""
    if not (request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    advance = get_object_or_404(StaffAdvance, pk=pk)
    advance.delete()
    return JsonResponse({'success': True, 'message': 'تم الحذف ✅'})


@login_required
@require_POST
def update_employee_salary(request):
    """تحديث المرتب ويوم القبض"""
    if not (request.user.is_owner or request.user.is_manager):
        return JsonResponse({'error': 'غير مصرح'}, status=403)

    employee_id = request.POST.get('employee_id')
    salary = request.POST.get('salary')
    payday = request.POST.get('payday')

    if not employee_id:
        return JsonResponse({'error': 'بيانات ناقصة'}, status=400)

    employee = get_object_or_404(User, pk=employee_id)

    if salary is not None:
        employee.salary = salary
    if payday is not None:
        employee.payday = int(payday)

    employee.save(update_fields=['salary', 'payday'])

    return JsonResponse({
        'success': True,
        'message': f'تم تحديث بيانات {employee.get_full_name() or employee.username} ✅'
    })
