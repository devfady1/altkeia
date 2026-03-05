from django.contrib import admin
from .models import InventoryItem, ProductIngredient, StockTransaction


class ProductIngredientInline(admin.TabularInline):
    model = ProductIngredient
    extra = 1


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'current_stock', 'minimum_stock', 'is_active']
    list_filter = ['unit', 'is_active']
    search_fields = ['name']
    inlines = [ProductIngredientInline]


@admin.register(ProductIngredient)
class ProductIngredientAdmin(admin.ModelAdmin):
    list_display = ['product', 'inventory_item', 'quantity_used']
    list_filter = ['inventory_item']
    search_fields = ['product__name', 'inventory_item__name']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['inventory_item', 'transaction_type', 'quantity', 'reason', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['inventory_item__name', 'reason']
    date_hierarchy = 'created_at'
