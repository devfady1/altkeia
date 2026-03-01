from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    """مستخدم النظام مع دعم الأدوار المتعددة"""

    class Role(models.TextChoices):
        OWNER = 'owner', 'مالك النظام'
        MANAGER = 'manager', 'مدير'
        CASHIER = 'cashier', 'كاشير'
        WAITER = 'waiter', 'ويتر'
        KITCHEN = 'kitchen', 'مطبخ'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WAITER,
        verbose_name='الدور'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    is_active_employee = models.BooleanField(default=True, verbose_name='موظف نشط')
    salary = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='المرتب الشهري'
    )
    payday = models.PositiveIntegerField(
        default=1, verbose_name='يوم القبض',
        help_text='يوم الشهر (1-28)'
    )

    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def __str__(self):
        return f"{self.get_full_name() or self.username} - {self.get_role_display()}"

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_cashier(self):
        return self.role == self.Role.CASHIER

    @property
    def is_waiter(self):
        return self.role == self.Role.WAITER

    @property
    def is_kitchen(self):
        return self.role == self.Role.KITCHEN


class StaffOrder(models.Model):
    """طلب موظف لنفسه (أكل/شرب من الكافيه)"""
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_orders',
        verbose_name='الموظف'
    )
    description = models.CharField(max_length=300, verbose_name='وصف الطلب')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    shift = models.ForeignKey(
        'reports.CashierShift',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_orders',
        verbose_name='الشيفت'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='التاريخ')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_staff_orders',
        verbose_name='أضيف بواسطة'
    )

    class Meta:
        verbose_name = 'طلب موظف'
        verbose_name_plural = 'طلبات الموظفين'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.description} ({self.amount})"


class StaffAdvance(models.Model):
    """سلفة للموظف"""
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_advances',
        verbose_name='الموظف'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    reason = models.CharField(max_length=300, blank=True, verbose_name='السبب')
    shift = models.ForeignKey(
        'reports.CashierShift',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_advances',
        verbose_name='الشيفت'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='التاريخ')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_staff_advances',
        verbose_name='أضيف بواسطة'
    )

    class Meta:
        verbose_name = 'سلفة'
        verbose_name_plural = 'السلف'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.amount}"
