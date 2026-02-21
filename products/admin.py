from django.contrib import admin
from .models import Category, Product, ProductSize


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 3
    fields = ('size', 'name', 'price', 'is_active', 'order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'has_sizes', 'is_available', 'is_active')
    list_filter = ('category', 'is_available', 'is_active', 'has_sizes')
    list_editable = ('price', 'is_available', 'has_sizes')
    inlines = [ProductSizeInline]


@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'display_name', 'price', 'is_active')
    list_filter = ('size', 'is_active')
    list_editable = ('price', 'is_active')
