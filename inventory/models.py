from django.db import models
from django.conf import settings
from decimal import Decimal


# ===== Unit Conversion System =====
# Maps (from_unit, to_unit) → multiplier
# e.g., 200 ml → liters = 200 * 0.001 = 0.2 liter
UNIT_CONVERSIONS = {
    ('ml', 'liter'): Decimal('0.001'),     # 1 ml = 0.001 liter
    ('liter', 'ml'): Decimal('1000'),      # 1 liter = 1000 ml
    ('g', 'kg'): Decimal('0.001'),         # 1 g = 0.001 kg
    ('kg', 'g'): Decimal('1000'),          # 1 kg = 1000 g
}


def convert_units(quantity, from_unit, to_unit):
    """
    تحويل الكمية من وحدة إلى أخرى.
    مثلاً: convert_units(200, 'ml', 'liter') → 0.2
    لو نفس الوحدة يرجع نفس الكمية.
    لو مفيش تحويل متاح يرجع None.
    """
    if from_unit == to_unit:
        return Decimal(str(quantity))
    key = (from_unit, to_unit)
    if key in UNIT_CONVERSIONS:
        return Decimal(str(quantity)) * UNIT_CONVERSIONS[key]
    return None


def get_compatible_units(unit):
    """
    إرجاع الوحدات المتوافقة مع وحدة معينة.
    مثلاً: get_compatible_units('liter') → ['ml', 'liter']
    """
    compatible = {unit}
    for (from_u, to_u) in UNIT_CONVERSIONS:
        if from_u == unit:
            compatible.add(to_u)
        elif to_u == unit:
            compatible.add(from_u)
    return list(compatible)



class InventoryItem(models.Model):
    """مادة خام في المخزون"""

    class Unit(models.TextChoices):
        MILLILITER = 'ml', 'ملليلتر (ml)'
        GRAM = 'g', 'جرام (g)'
        PIECE = 'piece', 'قطعة'
        BOTTLE = 'bottle', 'زجاجة'
        KILOGRAM = 'kg', 'كيلو (kg)'
        LITER = 'liter', 'لتر'
        PACK = 'pack', 'عبوة'
        PLATE = 'plate', 'طبق'
        LOAF = 'loaf', 'رغيف'

    name = models.CharField(max_length=200, verbose_name='اسم المادة')
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.PIECE,
        verbose_name='وحدة القياس'
    )
    current_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name='الكمية الحالية'
    )
    minimum_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name='الحد الأدنى',
        help_text='سيتم التنبيه عند وصول الكمية لهذا الحد'
    )
    cost_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='تكلفة الوحدة',
        help_text='اختياري - لحساب التكاليف'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مادة خام'
        verbose_name_plural = 'المواد الخام'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"

    @property
    def is_low_stock(self):
        """هل المخزون تحت الحد الأدنى؟"""
        return self.current_stock <= self.minimum_stock

    @property
    def stock_status(self):
        """حالة المخزون"""
        if self.current_stock <= 0:
            return 'out'
        elif self.current_stock <= self.minimum_stock:
            return 'low'
        return 'ok'


class ProductIngredient(models.Model):
    """ربط منتج بمادة خام - كم يحتاج كل منتج من كل مادة"""
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='المنتج'
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='product_usages',
        verbose_name='المادة الخام'
    )
    quantity_used = models.DecimalField(
        max_digits=10, decimal_places=3,
        verbose_name='الكمية المستخدمة',
        help_text='الكمية لكل وحدة من المنتج (بوحدة الاستخدام)'
    )
    usage_unit = models.CharField(
        max_length=20,
        choices=InventoryItem.Unit.choices,
        blank=True,
        verbose_name='وحدة الاستخدام',
        help_text='الوحدة اللي بتخصم بيها (لو فاضية هتستخدم نفس وحدة المادة الخام)'
    )

    class Meta:
        verbose_name = 'مكون منتج'
        verbose_name_plural = 'مكونات المنتجات'
        unique_together = ['product', 'inventory_item']

    def __str__(self):
        unit_display = self.get_usage_unit_display() if self.usage_unit else self.inventory_item.get_unit_display()
        return f"{self.product.name} ← {self.inventory_item.name} ({self.quantity_used} {unit_display})"

    @property
    def effective_usage_unit(self):
        """الوحدة الفعلية للاستخدام"""
        return self.usage_unit or self.inventory_item.unit

    @property
    def quantity_in_stock_unit(self):
        """
        الكمية محولة لوحدة المخزون.
        مثلاً: لو الاستخدام 200 ml والمخزون بالـ liter → 0.2 liter
        """
        from_unit = self.effective_usage_unit
        to_unit = self.inventory_item.unit
        converted = convert_units(self.quantity_used, from_unit, to_unit)
        if converted is not None:
            return converted
        # Fallback: no conversion available, use as-is
        return self.quantity_used


class StockTransaction(models.Model):
    """حركة مخزون - وارد أو صادر"""

    class TransactionType(models.TextChoices):
        IN = 'in', 'وارد'
        OUT = 'out', 'صادر'
        ADJUSTMENT = 'adjustment', 'تعديل جرد'
        WASTE = 'waste', 'هالك'

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='المادة الخام'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name='نوع الحركة'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='الكمية'
    )
    reason = models.CharField(
        max_length=200, blank=True,
        verbose_name='السبب'
    )
    reference_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_transactions',
        verbose_name='الطلب المرتبط'
    )
    shift = models.ForeignKey(
        'reports.CashierShift',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_transactions',
        verbose_name='الشيفت'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='بواسطة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='التاريخ')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'حركات المخزون'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.inventory_item.name} ({self.quantity})"
