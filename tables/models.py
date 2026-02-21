import uuid
from django.db import models
from core.models import Floor


class Table(models.Model):
    """طاولة في الكافيه"""

    class Status(models.TextChoices):
        EMPTY = 'empty', 'فارغة'
        OCCUPIED = 'occupied', 'مشغولة'
        PENDING = 'pending', 'طلبات معلقة'
        ACTIVITY = 'activity', 'نشاط شغال'
        RESERVED = 'reserved', 'محجوزة'

    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='tables', verbose_name='الطابق')
    number = models.PositiveIntegerField(verbose_name='رقم الطاولة')
    name = models.CharField(max_length=100, blank=True, verbose_name='اسم الطاولة')
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EMPTY,
        verbose_name='الحالة'
    )
    capacity = models.PositiveIntegerField(default=4, verbose_name='السعة')
    is_active = models.BooleanField(default=True, verbose_name='نشطة')
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True, verbose_name='QR Code')

    class Meta:
        verbose_name = 'طاولة'
        verbose_name_plural = 'الطاولات'
        ordering = ['floor', 'number']
        unique_together = ['floor', 'number']

    def __str__(self):
        return self.name or f"طاولة {self.number}"

    @property
    def display_name(self):
        return self.name or f"طاولة {self.number}"

    @property
    def status_color(self):
        colors = {
            'empty': '#2ecc71',
            'occupied': '#e74c3c',
            'pending': '#f39c12',
            'activity': '#9b59b6',
            'reserved': '#3498db',
        }
        return colors.get(self.status, '#95a5a6')
