from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order


@login_required
def order_list(request):
    orders = Order.objects.exclude(status='delivered').exclude(status='cancelled').select_related('table', 'session')
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def kitchen_view(request):
    """واجهة المطبخ - الطلبات المؤكدة فقط"""
    orders = Order.objects.filter(
        status__in=['confirmed', 'preparing']
    ).select_related('table').prefetch_related('items__product').order_by('created_at')
    return render(request, 'orders/kitchen.html', {'orders': orders})


@login_required
def kitchen_ticket(request, order_id):
    """طباعة تكت المطبخ"""
    order = get_object_or_404(
        Order.objects.select_related('table').prefetch_related('items__product'),
        pk=order_id
    )
    return render(request, 'orders/kitchen_ticket.html', {'order': order})
