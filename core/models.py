from django.db import models


class Floor(models.Model):
    """طابق في الكافيه"""
    name = models.CharField(max_length=100, verbose_name='اسم الطابق')
    order = models.PositiveIntegerField(default=0, verbose_name='الترتيب')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'طابق'
        verbose_name_plural = 'الطوابق'
        ordering = ['order']

    def __str__(self):
        return self.name


class SystemSettings(models.Model):
    """إعدادات النظام العامة"""
    cafe_name = models.CharField(max_length=200, default='كافيه', verbose_name='اسم الكافيه')
    logo = models.ImageField(upload_to='settings/', blank=True, null=True, verbose_name='الشعار')
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    address = models.TextField(blank=True, verbose_name='العنوان')
    currency = models.CharField(max_length=10, default='ج.م', verbose_name='العملة')
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الضريبة')

    class Meta:
        verbose_name = 'إعدادات النظام'
        verbose_name_plural = 'إعدادات النظام'

    def __str__(self):
        return self.cafe_name

    def save(self, *args, **kwargs):
        # Singleton pattern
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
