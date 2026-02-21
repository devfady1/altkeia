from django.contrib.auth.models import AbstractUser
from django.db import models


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
