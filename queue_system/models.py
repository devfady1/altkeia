from django.db import models
from activities.models import ActivityType


class QueueEntry(models.Model):
    """عنصر في الطابور"""

    class Status(models.TextChoices):
        WAITING = 'waiting', 'في الانتظار'
        ACTIVE = 'active', 'نشط'
        COMPLETED = 'completed', 'مكتمل'
        CANCELLED = 'cancelled', 'ملغي'

    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.CASCADE,
        related_name='queue_entries', verbose_name='نوع النشاط'
    )
    session = models.ForeignKey(
        'cafe_sessions.TableSession', on_delete=models.CASCADE,
        related_name='queue_entries',
        null=True, blank=True,
        verbose_name='الجلسة'
    )
    table = models.ForeignKey(
        'tables.Table', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='الطاولة'
    )
    customer_name = models.CharField(max_length=100, blank=True, verbose_name='اسم العميل')
    requested_hours = models.DecimalField(max_digits=4, decimal_places=1, default=1, verbose_name='عدد الساعات')
    position = models.PositiveIntegerField(default=0, verbose_name='الترتيب')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
        verbose_name='الحالة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت التسجيل')

    class Meta:
        verbose_name = 'عنصر طابور'
        verbose_name_plural = 'عناصر الطابور'
        ordering = ['activity_type', 'position']

    def __str__(self):
        return f"{self.customer_name or 'عميل'} - {self.activity_type.name} (#{self.position})"

    @property
    def waiting_count(self):
        """عدد المنتظرين قبله"""
        return QueueEntry.objects.filter(
            activity_type=self.activity_type,
            status=self.Status.WAITING,
            position__lt=self.position
        ).count()
