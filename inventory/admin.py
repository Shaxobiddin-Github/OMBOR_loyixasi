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
    list_display = ('name', 'sku', 'barcode', 'category', 'unit', 'min_stock', 'get_stock')
    list_filter = ('category', 'unit')
    search_fields = ('name', 'sku', 'barcode')
    ordering = ('name',)
    readonly_fields = ('uid', 'barcode', 'created_at', 'updated_at', 'qr_code_preview')
    
    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('name', 'sku', 'category')
        }),
        ('O\'lchov va Zaxira', {
            'fields': ('unit', 'min_stock')
        }),
        ('Tavsif', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Avtomatik Generatsiya (O\'zgartirish mumkin emas)', {
            'fields': ('uid', 'barcode', 'qr_code_preview'),
            'classes': ('collapse',)
        }),
        ('Vaqtlar', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_stock(self, obj):
        try:
            return f"{obj.stock.current_qty} {obj.unit}"
        except:
            return "0"
    get_stock.short_description = "Qoldiq"
    
    def qr_code_preview(self, obj):
        if obj.barcode:
            from django.utils.html import format_html
            from .qr_service import QRCodeService
            qr_data = QRCodeService.generate_qr_base64(obj.barcode, size=150)
            return format_html('<img src="{}" style="max-width:150px; border:1px solid #ccc; padding:5px;"/>', qr_data)
        return "-"
    qr_code_preview.short_description = "QR Kod"
    
    def save_model(self, request, obj, form, change):
        # Auto-generate barcode ONLY if not set
        if not obj.barcode:
            import time
            import random
            # Format: 13 digits (EAN-13 style)
            # 2 digits prefix (99 - internal) + 10 digits timestamp/random + 1 check/random
            timestamp = str(int(time.time()))[-8:] 
            random_part = str(random.randint(100, 999))
            obj.barcode = f"99{timestamp}{random_part}"
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }


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
