from django.http import JsonResponse
from django.views.decorators.http import require_GET
from products.models import Category, Product


@require_GET
def products_list_api(request):
    """Return all active products grouped by category with sizes"""
    categories = Category.objects.filter(is_active=True).prefetch_related(
        'products__sizes'
    )
    data = []
    for cat in categories:
        products = cat.products.filter(is_available=True, is_active=True)
        if products.exists():
            prods = []
            for p in products:
                prod_data = {
                    'id': p.pk,
                    'name': p.name,
                    'price': float(p.price),
                    'description': p.description,
                    'has_sizes': p.has_sizes,
                    'sizes': [],
                }
                if p.has_sizes:
                    for s in p.sizes.filter(is_active=True).order_by('order'):
                        prod_data['sizes'].append({
                            'id': s.pk,
                            'size': s.size,
                            'name': s.display_name,
                            'price': float(s.price),
                        })
                prods.append(prod_data)
            data.append({
                'id': cat.pk,
                'name': cat.name,
                'icon': cat.icon,
                'products': prods,
            })
    return JsonResponse({'categories': data})
