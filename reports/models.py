from django.db import models
from django.conf import settings
from django.utils import timezone


class CashierShift(models.Model):
    """شيفت الكاشير"""

    class ShiftType(models.TextChoices):
        MORNING = 'morning', 'صباحي'
        AFTERNOON = 'afternoon', 'بيات'
        NIGHT = 'night', 'ليلي'

    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='started_shifts',
        verbose_name='بدأ بواسطة'
    )
    shift_type = models.CharField(
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.MORNING,
        verbose_name='نوع الشيفت'
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت البداية')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت النهاية')
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ended_shifts',
        verbose_name='أنهى بواسطة'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    # Computed on close
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='إجمالي الإيرادات'
    )
    total_orders = models.PositiveIntegerField(default=0, verbose_name='عدد الطلبات')
    total_sessions = models.PositiveIntegerField(default=0, verbose_name='عدد الجلسات')
    total_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='إجمالي الخصومات'
    )
    total_activities_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='إيرادات الأنشطة'
    )
    total_activities_count = models.PositiveIntegerField(
        default=0, verbose_name='عدد الأنشطة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'شيفت'
        verbose_name_plural = 'الشيفتات'
        ordering = ['-started_at']

    def __str__(self):
        status = 'نشط' if self.is_active else 'مغلق'
        return f"شيفت {self.get_shift_type_display()} #{self.pk} - {self.started_by} ({status})"

    @property
    def duration(self):
        """مدة الشيفت"""
        end = self.ended_at or timezone.now()
        delta = end - self.started_at
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours} ساعة و {minutes} دقيقة"

    @property
    def duration_seconds(self):
        """مدة الشيفت بالثواني (للتايمر)"""
        end = self.ended_at or timezone.now()
        delta = end - self.started_at
        return int(delta.total_seconds())

    def recalculate_totals(self):
        """إعادة حساب إجماليات الشيفت بناءً على العمليات الفعلية"""
        from payments.models import Payment
        from orders.models import Order
        from sessions.models import TableSession
        from activities.models import ActivitySession

        timestamp = self.ended_at or timezone.now()

        # Payments during this shift
        payments = Payment.objects.filter(
            paid_at__gte=self.started_at,
            paid_at__lte=timestamp
        )
        self.total_revenue = payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.total_discount = payments.aggregate(
            total=models.Sum('discount')
        )['total'] or 0

        # Orders during this shift
        orders = Order.objects.filter(
            created_at__gte=self.started_at,
            created_at__lte=timestamp
        ).exclude(status=Order.Status.CANCELLED)
        self.total_orders = orders.count()

        # Sessions closed during this shift
        sessions = TableSession.objects.filter(
            opened_at__gte=self.started_at,
            opened_at__lte=timestamp,
            status='closed'
        )
        self.total_sessions = sessions.count()

        # Activities during this shift
        activities = ActivitySession.objects.filter(
            started_at__gte=self.started_at,
            started_at__lte=timestamp,
            ended_at__isnull=False
        )
        self.total_activities_revenue = activities.aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        self.total_activities_count = activities.count()
        self.save(update_fields=['total_revenue', 'total_discount', 'total_orders', 'total_sessions', 'total_activities_revenue', 'total_activities_count'])


    def close_shift(self, user=None):
        """إغلاق الشيفت وحساب الإجماليات"""
        now = timezone.now()
        self.ended_at = now
        self.ended_by = user
        self.is_active = False
        self.save(update_fields=['ended_at', 'ended_by', 'is_active'])
        self.recalculate_totals()
