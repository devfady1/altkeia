from .models import CashierShift


def active_shift(request):
    """Inject active shift into all templates for navbar display"""
    shift = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        shift = CashierShift.objects.filter(is_active=True).first()
    return {'active_shift': shift}
