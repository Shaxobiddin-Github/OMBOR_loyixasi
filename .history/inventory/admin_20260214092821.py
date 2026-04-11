"""
Inventory admin configuration.
"""
import time
import random
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.html import format_html

from .models import Employee, Category, Product, Stock, Movement, MovementItem
from .face_service import FaceService
from .qr_service import QRCodeService

# ==========================================
# 1. EMPLOYEE (Xodimlar) ADMINI
# ==========================================
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id', 'face_label', 'is_active', 'is_commander', 'face_data_status', 'created_at')
    list_filter = ('is_active', 'is_commander')
    search_fields = ('name', 'employee_id')
    filter_horizontal = ('assigned_categories',) # Shu joyda Jazzmin xato berayotgan edi
    ordering = ('name',)
    actions = ['reset_face_data']

    # Yuzni o'chirish uchun maxsus URL qo'shish
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('delete-face/<int:employee_id>/', self.admin_site.admin_view(self.delete_face_view), name='employee-face-delete'),
        ]
        return custom_urls + urls

    # Yuzni o'chirish funksiyasi
    def delete_face_view(self, request, employee_id):
        employee = get_object_or_404(Employee, id=employee_id)
        service = FaceService()
        
        if service.delete_employee_model(employee.face_label):
            self.message_user(request, f"✅ {employee.name} uchun face model o'chirildi.", messages.SUCCESS)
        else:
            self.message_user(request, f"⚠️ {employee.name} uchun model topilmadi.", messages.WARNING)
        
        return redirect('admin:inventory_employee_changelist')

    # Yuz ma'lumotlari holatini tugma ko'rinishida chiqarish
    def face_data_status(self, obj):
        service = FaceService()
        if service.employee_model_exists(obj.face_label):
            url = reverse('admin:employee-face-delete', args=[obj.id])
            return format_html(
                '<a href="{}" class="button" style="background:#fee2e2; color:#b91c1c; padding:3px 8px; border-radius:4px; text-decoration:none;">🗑️ O\'chirish</a>',
                url
            )
        return format_html('<span style="color:#94a3b8;">—</span>')
    
    face_data_status.short_description = "Face Model"
    face_data_status.allow_tags = True

    # Ommaviy harakatlar (Action) orqali yuzlarni tozalash
    @admin.action(description="🗑️ Face ma'lumotlarini tozalash (qayta ro'yxatdan o'tkazish uchun)")
    def reset_face_data(self, request, queryset):
        service = FaceService()
        deleted, skipped = [], []

        for emp in queryset:
            if service.delete_employee_model(emp.face_label):
                deleted.append(emp.name)
            else:
                skipped.append(emp.name)

        msg = ""
        if deleted:
            msg += f"✅ {len(deleted)} ta xodimning face modeli o'chirildi: {', '.join(deleted)}. "
        if skipped:
            msg += f"⚠️ {len(skipped)} ta xodimning modeli topilmadi: {', '.join(skipped)}."
        if not deleted and not skipped:
            msg = "Hech narsa tanlanmadi."

        self.message_user(request, msg)

    # JAZZMIN CSS XATOSINI TO'G'IRLASH UCHUN MEDIA QO'SHILDI
    class Media:
        css = {
            'all': ('css/jazzmin_fix.css',)
        }


# ==========================================
# 2. CATEGORY (Toifalar) ADMINI
# ==========================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


# ==========================================
# 3. PRODUCT (Mahsulotlar) ADMINI
# ==========================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'barcode', 'category', 'unit', 'min_stock', 'get_stock')
    list_filter = ('category', 'unit')
    search_fields = ('name', 'sku', 'barcode')
    ordering = ('name',)
    readonly_fields = ('uid', 'barcode', 'created_at', 'updated_at', 'qr_code_preview')
    
    # Maydonlarni guruhlarga bo'lib ko'rsatish
    fieldsets = (
        ('Asosiy Ma\'lumotlar', {'fields': ('name', 'sku', 'category')}),
        ('O\'lchov va Zaxira', {'fields': ('unit', 'min_stock')}),
        ('Tavsif', {'fields': ('description',), 'classes': ('collapse',)}),
        ('Avtomatik Generatsiya (O\'zgartirish mumkin emas)', {'fields': ('uid', 'barcode', 'qr_code_preview'), 'classes': ('collapse',)}),
        ('Vaqtlar', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    # Ombor qoldig'ini olish
    def get_stock(self, obj):
        try:
            return f"{obj.stock.current_qty} {obj.unit}"
        except:
            return "0"
    get_stock.short_description = "Qoldiq"
    
    # QR kodni generatsiya qilib ko'rsatish
    def qr_code_preview(self, obj):
        if obj.barcode:
            qr_data = QRCodeService.generate_qr_base64(obj.barcode, size=150)
            return format_html('<img src="{}" style="max-width:150px; border:1px solid #ccc; padding:5px;"/>', qr_data)
        return "-"
    qr_code_preview.short_description = "QR Kod"
    
    # Mahsulotni saqlashdan oldin shtrix kod generatsiya qilish
    def save_model(self, request, obj, form, change):
        if not obj.barcode:
            timestamp = str(int(time.time()))[-8:] 
            random_part = str(random.randint(100, 999))
            obj.barcode = f"99{timestamp}{random_part}"
        super().save_model(request, obj, form, change)
    
    # Kiritilgan qo'shimcha CSS fayllar
    class Media:
        css = {
            'all': ('css/admin_custom.css', 'css/jazzmin_fix.css',)
        }


# ==========================================
# 4. STOCK (Ombor qoldig'i) ADMINI
# ==========================================
@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'current_qty', 'last_updated')
    search_fields = ('product__name', 'product__sku')
    ordering = ('product__name',)


# ==========================================
# 5. MOVEMENT (Harakatlar va uning detallari)
# ==========================================
class MovementItemInline(admin.TabularInline):
    model = MovementItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price')


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'movement_type', 'status', 'performed_by', 'face_employee', 'face_verified', 'created_at')
    list_filter = ('movement_type', 'status', 'face_verified')
    search_fields = ('performed_by__username', 'face_employee__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'face_verified_at', 'face_confidence', 'reversed_movement')
    inlines = [MovementItemInline]


@admin.register(MovementItem)
class MovementItemAdmin(admin.ModelAdmin):
    list_display = ('movement', 'product', 'quantity', 'unit_price')
    list_filter = ('movement__movement_type',)
    search_fields = ('product__name', 'movement__id')