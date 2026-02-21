from django.db import models


class Category(models.Model):
    """تصنيف المنتجات"""
    name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
    icon = models.CharField(max_length=50, blank=True, default='☕', verbose_name='أيقونة')
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name='صورة')
    order = models.PositiveIntegerField(default=0, verbose_name='الترتيب')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'تصنيف'
        verbose_name_plural = 'التصنيفات'
        ordering = ['order']

    def __str__(self):
        return self.name


class Product(models.Model):
    """منتج في المنيو"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='التصنيف')
    name = models.CharField(max_length=200, verbose_name='اسم المنتج')
    description = models.TextField(blank=True, verbose_name='الوصف')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='السعر الافتراضي')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='صورة')
    is_available = models.BooleanField(default=True, verbose_name='متاح')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    preparation_time = models.PositiveIntegerField(default=5, verbose_name='وقت التحضير (دقائق)')
    has_sizes = models.BooleanField(default=False, verbose_name='له أحجام مختلفة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering = ['category__order', 'name']

    def __str__(self):
        return f"{self.name} - {self.price}"

    def get_sizes(self):
        """Return sizes if product has them, else return a single default"""
        if self.has_sizes:
            return self.sizes.filter(is_active=True).order_by('order')
        return []


class ProductSize(models.Model):
    """حجم المنتج - صغير، وسط، كبير"""

    class SizeChoice(models.TextChoices):
        SMALL = 'small', 'صغير'
        MEDIUM = 'medium', 'وسط'
        LARGE = 'large', 'كبير'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes', verbose_name='المنتج')
    size = models.CharField(max_length=20, choices=SizeChoice.choices, verbose_name='الحجم')
    name = models.CharField(max_length=50, blank=True, verbose_name='اسم مخصص',
                            help_text='اتركه فارغ لاستخدام الاسم الافتراضي')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='السعر')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    order = models.PositiveIntegerField(default=0, verbose_name='الترتيب')

    class Meta:
        verbose_name = 'حجم منتج'
        verbose_name_plural = 'أحجام المنتجات'
        ordering = ['order']
        unique_together = ['product', 'size']

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.price})"

    @property
    def display_name(self):
        return self.name or self.get_size_display()
