"""
Inventory admin configuration.
"""
from django.contrib import admin
from .models import Employee, Category, Product, Stock, Movement, MovementItem


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id', 'face_label', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'employee_id')
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'barcode', 'category', 'unit', 'min_stock')
    list_filter = ('category',)
    search_fields = ('name', 'sku', 'barcode')
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'current_qty', 'last_updated')
    search_fields = ('product__name', 'product__sku')
    ordering = ('product__name',)


class MovementItemInline(admin.TabularInline):
    model = MovementItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price')


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'movement_type', 'status', 'performed_by', 
        'face_employee', 'face_verified', 'created_at'
    )
    list_filter = ('movement_type', 'status', 'face_verified')
    search_fields = ('performed_by__username', 'face_employee__name')
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'face_verified_at', 
        'face_confidence', 'reversed_movement'
    )
    inlines = [MovementItemInline]


@admin.register(MovementItem)
class MovementItemAdmin(admin.ModelAdmin):
    list_display = ('movement', 'product', 'quantity', 'unit_price')
    list_filter = ('movement__movement_type',)
    search_fields = ('product__name', 'movement__id')
