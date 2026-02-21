from django.db import models
from django.conf import settings
from django.utils import timezone
from tables.models import Table


class TableSession(models.Model):
    """جلسة على طاولة"""

    class Status(models.TextChoices):
        OPEN = 'open', 'مفتوحة'
        ACTIVE = 'active', 'نشطة'
        CLOSED = 'closed', 'مغلقة'

    tables = models.ManyToManyField(Table, related_name='sessions_set', verbose_name='الطاولات')
    primary_table = models.ForeignKey(
        Table, on_delete=models.CASCADE,
        related_name='primary_sessions', verbose_name='الطاولة الرئيسية'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name='الحالة'
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='opened_sessions',
        verbose_name='فُتحت بواسطة'
    )
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الفتح')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت الإغلاق')
    total_orders = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='إجمالي الطلبات')
    total_activities = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='إجمالي الأنشطة')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='الإجمالي')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    guest_count = models.PositiveIntegerField(default=1, verbose_name='عدد الضيوف')

    class Meta:
        verbose_name = 'جلسة'
        verbose_name_plural = 'الجلسات'
        ordering = ['-opened_at']

    def __str__(self):
        return f"جلسة #{self.pk} - {self.primary_table}"

    def calculate_total(self):
        """حساب الإجمالي"""
        from orders.models import Order
        from activities.models import ActivitySession

        orders_total = sum(
            item.price * item.quantity
            for order in self.orders.exclude(status=Order.Status.CANCELLED)
            for item in order.items.all()
        )
        activities_total = sum(
            a.total_price or 0
            for a in self.activity_sessions.filter(ended_at__isnull=False)
        )
        self.total_orders = orders_total
        self.total_activities = activities_total
        self.total_amount = orders_total + activities_total
        self.save(update_fields=['total_orders', 'total_activities', 'total_amount'])

    def close_session(self, user=None):
        """إغلاق الجلسة وتحرير الطاولات"""
        self.calculate_total()
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save()
        # تحرير الطاولات
        self.tables.all().update(status=Table.Status.EMPTY)

    def merge_table(self, table):
        """دمج طاولة أخرى في الجلسة"""
        self.tables.add(table)
        table.status = Table.Status.OCCUPIED
        table.save()

    @property
    def duration(self):
        """مدة الجلسة"""
        end = self.closed_at or timezone.now()
        delta = end - self.opened_at
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours} ساعة و {minutes} دقيقة"
