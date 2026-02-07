"""
Stock management services with atomic operations.
- process_movement: Finalize PENDING movement with Face ID
- reverse_movement: Admin-only reversal
"""
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Movement, MovementItem, Stock, Employee


class StockService:
    """
    Service for atomic stock operations.
    Uses select_for_update() for row-level locking.
    """
    
    @staticmethod
    @transaction.atomic
    def process_movement(movement: Movement, employee_id: int, confidence: float):
        """
        Finalize a PENDING movement with Face ID verification.
        
        Args:
            movement: Movement instance (must be PENDING)
            employee_id: Verified employee ID from Face service
            confidence: Face match confidence score
        
        Raises:
            ValidationError: If movement is not PENDING or insufficient stock
        """
        if movement.status != 'PENDING':
            raise ValidationError("Faqat PENDING holatdagi harakat yakunlanishi mumkin")
        
        # Get verified employee
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            raise ValidationError("Xodim topilmadi")
        
        # Set face verification fields
        movement.face_employee = employee
        movement.face_verified = True
        movement.face_confidence = confidence
        movement.face_verified_at = timezone.now()
        
        # Process each item with row-level lock
        items = movement.items.select_for_update().select_related('product')
        
        for item in items:
            # Get or create stock with lock
            stock, created = Stock.objects.select_for_update().get_or_create(
                product=item.product,
                defaults={'current_qty': 0}
            )
            
            if movement.movement_type == 'OUT':
                # Check sufficient stock
                if stock.current_qty < item.quantity:
                    raise ValidationError(
                        f"{item.product.name}: "
                        f"Mavjud zaxira {stock.current_qty} {item.product.unit}, "
                        f"so'ralgan {item.quantity} {item.product.unit}"
                    )
                stock.current_qty -= item.quantity
            else:  # IN
                stock.current_qty += item.quantity
            
            stock.save()
        
        movement.status = 'VERIFIED'
        movement.save()
        
        return movement
    
    @staticmethod
    @transaction.atomic
    def reverse_movement(movement: Movement, user, reason: str) -> Movement:
        """
        Create a reversal movement. Admin-only operation.
        
        - Original IN → creates OUT reversal
        - Original OUT → creates IN reversal
        - Quantities always positive
        - Original movement marked as CANCELLED
        
        Args:
            movement: Movement to reverse (must be VERIFIED)
            user: User performing the reversal (must be admin)
            reason: Reason for reversal
        
        Returns:
            The new reversal Movement
            
        Raises:
            ValidationError: If not allowed
        """
        # Check admin permission
        if user.role != 'admin':
            raise ValidationError("Faqat admin bekor qilishi mumkin")
        
        # Check movement status
        if movement.status != 'VERIFIED':
            raise ValidationError("Faqat VERIFIED holatdagi harakat bekor qilinishi mumkin")
        
        # Check not already reversed
        if movement.reversed_movement is not None:
            raise ValidationError("Bu harakat allaqachon bekor qilingan")
        
        # Check no existing reversal for this movement
        if Movement.objects.filter(reversed_movement=movement).exists():
            raise ValidationError("Bu harakat uchun bekor qilish allaqachon mavjud")
        
        # Determine reverse type
        reverse_type = 'OUT' if movement.movement_type == 'IN' else 'IN'
        
        # Create reversal movement
        reversal = Movement.objects.create(
            movement_type=reverse_type,
            status='VERIFIED',
            performed_by=user,
            face_employee=movement.face_employee,
            face_verified=True,
            face_confidence=0,
            face_verified_at=timezone.now(),
            note=f"Bekor qilish sababi: {reason}",
            reversed_movement=movement,
        )
        
        # Create reversal items and update stock
        for item in movement.items.all():
            MovementItem.objects.create(
                movement=reversal,
                product=item.product,
                quantity=item.quantity,  # Always positive
                unit_price=item.unit_price,
            )
            
            # Update stock
            stock = Stock.objects.select_for_update().get(product=item.product)
            if reverse_type == 'IN':
                stock.current_qty += item.quantity
            else:  # OUT (reversing an IN)
                stock.current_qty -= item.quantity
            stock.save()
        
        # Mark original as cancelled
        movement.status = 'CANCELLED'
        movement.save()
        
        return reversal
    
    @staticmethod
    def get_stock_summary():
        """Get summary of stock levels."""
        from django.db.models import Sum, Count, Q
        
        stocks = Stock.objects.select_related('product', 'product__category')
        
        total_products = stocks.count()
        low_stock_count = sum(1 for s in stocks if s.is_low_stock)
        total_value = stocks.aggregate(
            total=Sum(F('current_qty') * F('product__movementitem__unit_price'))
        )['total'] or 0
        
        return {
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'total_value': total_value,
        }
