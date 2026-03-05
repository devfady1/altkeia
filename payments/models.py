from django.db import models
from django.conf import settings
from sessions.models import TableSession


class Payment(models.Model):
    """عملية دفع"""

    class Method(models.TextChoices):
        CASH = 'cash', 'كاش'
        CARD = 'card', 'بطاقة'

    session = models.ForeignKey(
        TableSession, on_delete=models.CASCADE,
        related_name='payments', verbose_name='الجلسة',
        null=True, blank=True
    )
    activity_session = models.ForeignKey(
        'activities.ActivitySession', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments',
        verbose_name='جلسة النشاط'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='المبلغ المرتجع')
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.CASH,
        verbose_name='طريقة الدفع'
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_payments',
        verbose_name='الكاشير'
    )
    paid_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الدفع')
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='الخصم')
    shift = models.ForeignKey(
        'reports.CashierShift',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments',
        verbose_name='الشيفت'
    )
    shift_invoice_number = models.PositiveIntegerField(
        default=0,
        verbose_name='رقم الفاتورة في الشيفت'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'عملية دفع'
        verbose_name_plural = 'عمليات الدفع'
        ordering = ['-paid_at']

    def __str__(self):
        return f"دفع #{self.pk} - {self.amount}"

    @property
    def final_amount(self):
        return self.amount - self.discount
