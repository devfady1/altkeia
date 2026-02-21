from django.db import models
from django.conf import settings
from sessions.models import TableSession


class Payment(models.Model):
    """عملية دفع"""

    class Method(models.TextChoices):
        CASH = 'cash', 'كاش'
        CARD = 'card', 'بطاقة'

    session = models.OneToOneField(
        TableSession, on_delete=models.CASCADE,
        related_name='payment', verbose_name='الجلسة'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
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
