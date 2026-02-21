from django.db import models
from django.utils import timezone
from decimal import Decimal
import math


class ActivityType(models.Model):
    """نوع النشاط"""
    name = models.CharField(max_length=100, verbose_name='اسم النشاط')
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='سعر الساعة')
    icon = models.CharField(max_length=50, default='🎮', verbose_name='أيقونة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'نوع نشاط'
        verbose_name_plural = 'أنواع الأنشطة'

    def __str__(self):
        return f"{self.name} - {self.price_per_hour}/ساعة"


class Device(models.Model):
    """جهاز (PlayStation / بلياردو / بينج بونج)"""

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'متاح'
        BUSY = 'busy', 'مشغول'
        MAINTENANCE = 'maintenance', 'صيانة'

    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.CASCADE,
        related_name='devices', verbose_name='نوع النشاط'
    )
    name = models.CharField(max_length=100, verbose_name='اسم الجهاز')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        verbose_name='الحالة'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'جهاز'
        verbose_name_plural = 'الأجهزة'

    def __str__(self):
        return f"{self.name} ({self.activity_type.name})"


class ActivitySession(models.Model):
    """جلسة نشاط"""
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='activity_sessions', verbose_name='الجهاز')
    session = models.ForeignKey(
        'cafe_sessions.TableSession', on_delete=models.CASCADE,
        related_name='activity_sessions', verbose_name='جلسة الطاولة'
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت البدء')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت الانتهاء')
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='الإجمالي')

    class Meta:
        verbose_name = 'جلسة نشاط'
        verbose_name_plural = 'جلسات الأنشطة'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.device.name} - جلسة #{self.session.pk}"

    @property
    def duration_minutes(self):
        end = self.ended_at or timezone.now()
        delta = end - self.started_at
        return delta.total_seconds() / 60

    @property
    def duration_display(self):
        mins = int(self.duration_minutes)
        hours = mins // 60
        remaining = mins % 60
        return f"{hours}:{remaining:02d}"

    @property
    def running_cost(self):
        """التكلفة الحالية"""
        hours = Decimal(str(math.ceil(self.duration_minutes / 60)))
        return hours * self.device.activity_type.price_per_hour

    def end_activity(self):
        """إنهاء النشاط وحساب السعر"""
        self.ended_at = timezone.now()
        hours = Decimal(str(math.ceil(self.duration_minutes / 60)))
        self.total_price = hours * self.device.activity_type.price_per_hour
        self.save()
        # تحرير الجهاز
        self.device.status = Device.Status.AVAILABLE
        self.device.save()
