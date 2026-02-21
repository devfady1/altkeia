from django.db import models
from django.conf import settings
from sessions.models import TableSession
from tables.models import Table
from products.models import Product, ProductSize


class Order(models.Model):
    """طلب"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'معلق'
        CONFIRMED = 'confirmed', 'مؤكد'
        PREPARING = 'preparing', 'قيد التحضير'
        READY = 'ready', 'جاهز'
        DELIVERED = 'delivered', 'تم التوصيل'
        CANCELLED = 'cancelled', 'ملغي'

    session = models.ForeignKey(
        TableSession, on_delete=models.CASCADE,
        related_name='orders', verbose_name='الجلسة'
    )
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE,
        related_name='orders', verbose_name='الطاولة'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='الحالة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الطلب')
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_orders',
        verbose_name='مؤكد بواسطة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_from_qr = models.BooleanField(default=False, verbose_name='من QR')

    class Meta:
        verbose_name = 'طلب'
        verbose_name_plural = 'الطلبات'
        ordering = ['-created_at']

    def __str__(self):
        return f"طلب #{self.pk} - {self.table}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def status_color(self):
        colors = {
            'pending': '#f39c12',
            'confirmed': '#3498db',
            'preparing': '#e67e22',
            'ready': '#2ecc71',
            'delivered': '#27ae60',
            'cancelled': '#e74c3c',
        }
        return colors.get(self.status, '#95a5a6')


class OrderItem(models.Model):
    """عنصر في الطلب"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='الطلب')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='المنتج')
    size = models.ForeignKey(
        ProductSize, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='الحجم'
    )
    size_name = models.CharField(max_length=50, blank=True, verbose_name='اسم الحجم')
    quantity = models.PositiveIntegerField(default=1, verbose_name='الكمية')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='السعر')
    notes = models.CharField(max_length=500, blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'عنصر طلب'
        verbose_name_plural = 'عناصر الطلب'

    def __str__(self):
        size_str = f" ({self.size_name})" if self.size_name else ""
        return f"{self.product.name}{size_str} x{self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity

    @property
    def display_name(self):
        if self.size_name:
            return f"{self.product.name} ({self.size_name})"
        return self.product.name

    def save(self, *args, **kwargs):
        if not self.price:
            if self.size:
                self.price = self.size.price
            else:
                self.price = self.product.price
        if self.size and not self.size_name:
            self.size_name = self.size.display_name
        super().save(*args, **kwargs)
