from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Floor, SystemSettings
from tables.models import Table
from products.models import Category, Product
from activities.models import ActivityType, Device
from accounts.models import User


@login_required
def home(request):
    return redirect('dashboard')


@login_required
def manage_view(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
    return render(request, 'core/manage.html')


@login_required
def manage_floors(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            Floor.objects.create(
                name=request.POST.get('name'),
                order=request.POST.get('order', 0)
            )
        elif action == 'delete':
            Floor.objects.filter(pk=request.POST.get('id')).delete()
        elif action == 'toggle':
            floor = get_object_or_404(Floor, pk=request.POST.get('id'))
            floor.is_active = not floor.is_active
            floor.save()
        return redirect('manage_floors')

    floors = Floor.objects.all()
    return render(request, 'core/manage_floors.html', {'floors': floors})


@login_required
def manage_tables(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            table = Table.objects.create(
                floor_id=request.POST.get('floor'),
                number=request.POST.get('number'),
                name=request.POST.get('name', ''),
                capacity=request.POST.get('capacity', 4)
            )
            # Generate QR code
            _generate_qr(table, request)
        elif action == 'generate_qr':
            table = get_object_or_404(Table, pk=request.POST.get('id'))
            _generate_qr(table, request)
        elif action == 'delete':
            Table.objects.filter(pk=request.POST.get('id')).delete()
        return redirect('manage_tables')

    tables = Table.objects.select_related('floor').all()
    floors = Floor.objects.filter(is_active=True)
    return render(request, 'core/manage_tables.html', {'tables': tables, 'floors': floors})


def _generate_qr(table, request):
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile
    url = f"{request.scheme}://{request.get_host()}/qr/{table.uuid}/"
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format='PNG')
    table.qr_code.save(f'table_{table.pk}.png', ContentFile(buf.getvalue()))


@login_required
def manage_products(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_category':
            Category.objects.create(
                name=request.POST.get('name'),
                icon=request.POST.get('icon', '☕'),
                order=request.POST.get('order', 0)
            )
        elif action == 'add_product':
            Product.objects.create(
                category_id=request.POST.get('category'),
                name=request.POST.get('name'),
                price=request.POST.get('price'),
                description=request.POST.get('description', '')
            )
        elif action == 'delete_product':
            Product.objects.filter(pk=request.POST.get('id')).delete()
        elif action == 'toggle_product':
            p = get_object_or_404(Product, pk=request.POST.get('id'))
            p.is_available = not p.is_available
            p.save()
        return redirect('manage_products')

    categories = Category.objects.prefetch_related('products').all()
    return render(request, 'core/manage_products.html', {'categories': categories})


@login_required
def manage_devices(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_type':
            ActivityType.objects.create(
                name=request.POST.get('name'),
                price_per_hour=request.POST.get('price_per_hour'),
                icon=request.POST.get('icon', '🎮')
            )
        elif action == 'add_device':
            Device.objects.create(
                activity_type_id=request.POST.get('activity_type'),
                name=request.POST.get('name')
            )
        elif action == 'delete_device':
            Device.objects.filter(pk=request.POST.get('id')).delete()
        return redirect('manage_devices')

    activity_types = ActivityType.objects.prefetch_related('devices').all()
    return render(request, 'core/manage_devices.html', {'activity_types': activity_types})


@login_required
def manage_employees(request):
    if not (request.user.is_owner or request.user.is_manager):
        return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            User.objects.create_user(
                username=request.POST.get('username'),
                password=request.POST.get('password'),
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                role=request.POST.get('role'),
                phone=request.POST.get('phone', '')
            )
        elif action == 'delete':
            User.objects.filter(pk=request.POST.get('id')).exclude(role='owner').delete()
        elif action == 'toggle':
            emp = get_object_or_404(User, pk=request.POST.get('id'))
            emp.is_active_employee = not emp.is_active_employee
            emp.save()
        return redirect('manage_employees')

    employees = User.objects.all().order_by('role')
    return render(request, 'core/manage_employees.html', {'employees': employees})
