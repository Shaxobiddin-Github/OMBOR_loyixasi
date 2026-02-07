"""
Inventory models for warehouse management.
- Employee: Face ID registration
- Category, Product: Product catalog
- Stock: Current inventory levels
- Movement, MovementItem: Stock movements (IN/OUT)
"""
import uuid
from django.db import models
from django.conf import settings


class Employee(models.Model):
    """Employee with Face ID registration."""
    name = models.CharField(max_length=100, verbose_name="Ism")
    employee_id = models.CharField(max_length=50, unique=True, verbose_name="Xodim ID")
    photo = models.ImageField(upload_to='employees/', blank=True, null=True, verbose_name="Rasm")
    face_label = models.IntegerField(unique=True, verbose_name="Face Label (LBPH)")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Xodim"
        verbose_name_plural = "Xodimlar"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class Category(models.Model):
    """Product category."""
    name = models.CharField(max_length=100, verbose_name="Kategoriya nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product with QR/Barcode support."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    name = models.CharField(max_length=200, db_index=True, verbose_name="Mahsulot nomi")
    sku = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="SKU")
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products',
        verbose_name="Kategoriya"
    )
    barcode = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True, 
        verbose_name="Shtrix kod (QR)"
    )
    unit = models.CharField(max_length=20, verbose_name="O'lchov birligi")  # dona, kg, metr
    min_stock = models.IntegerField(default=0, verbose_name="Minimal zaxira")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering = ['name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Stock(models.Model):
    """Current stock levels. Auto-created via signal when Product is created."""
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='stock',
        verbose_name="Mahsulot"
    )
    current_qty = models.IntegerField(default=0, verbose_name="Joriy miqdor")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zaxira"
        verbose_name_plural = "Zaxiralar"
        indexes = [
            models.Index(fields=['current_qty']),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.current_qty} {self.product.unit}"
    
    @property
    def is_low_stock(self):
        return self.current_qty <= self.product.min_stock


class Movement(models.Model):
    """Stock movement record. Never deleted - use reversal instead."""
    
    MOVEMENT_TYPES = [
        ('IN', 'Kirim'),
        ('OUT', 'Chiqim'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('VERIFIED', 'Tasdiqlangan'),
        ('CANCELLED', 'Bekor qilingan'),
    ]
    
    movement_type = models.CharField(
        max_length=10, 
        choices=MOVEMENT_TYPES, 
        db_index=True,
        verbose_name="Turi"
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='PENDING', 
        db_index=True,
        verbose_name="Holat"
    )
    
    # Who performed the operation (logged-in user)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name="Bajaruvchi"
    )
    
    # Face ID verification fields
    face_employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name="Face ID xodim"
    )
    face_verified = models.BooleanField(default=False, verbose_name="Face tasdiqlandi")
    face_confidence = models.FloatField(null=True, blank=True, verbose_name="Face ishonch darajasi")
    face_verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Face tasdiqlash vaqti")
    
    # Timestamps and notes
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=True, verbose_name="Izoh")
    
    # For reversal - points to original movement that was cancelled
    reversed_movement = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reversals',
        verbose_name="Bekor qilingan movement"
    )

    class Meta:
        verbose_name = "Harakat"
        verbose_name_plural = "Harakatlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['performed_by']),
            models.Index(fields=['face_employee']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} #{self.id} - {self.get_status_display()}"
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class MovementItem(models.Model):
    """Individual item in a movement. Quantity is always positive."""
    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Harakat"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='movement_items',
        verbose_name="Mahsulot"
    )
    quantity = models.PositiveIntegerField(verbose_name="Miqdor")
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Birlik narxi"
    )

    class Meta:
        verbose_name = "Harakat elementi"
        verbose_name_plural = "Harakat elementlari"
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['movement']),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
