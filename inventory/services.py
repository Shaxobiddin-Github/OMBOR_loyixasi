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
        movement.face_verified = True
        movement.face_confidence = confidence
        movement.face_verified_at = timezone.now()
        movement.face_employee = employee  # Save the Actor

        # Permission Check (Hierarchy)
        # Agar harakat aniq bir xodimga (target_employee) tegishli bo'lsa,
        # Face Verify qilgan odam (employee) shu xodimning o'zi yoki rahbari bo'lishi kerak.
        if movement.target_employee:
            # 1. Self check
            if employee.id != movement.target_employee.id:
                # 2. Supervisor check
                if movement.target_employee.supervisor_id != employee.id:
                    raise ValidationError(
                        f"Ruxsat yo'q: {employee.name} {movement.target_employee.name} ning rahbari emas."
                    )
                # Auto-Remark for Delegation
                delegation_note = f"Komandir {employee.name} -> xodim {movement.target_employee.name} uchun kirim"
                if movement.note:
                    movement.note = f"{delegation_note}. {movement.note}"
                else:
                    movement.note = delegation_note
        
        # Process each item with row-level lock
        items = movement.items.select_for_update().select_related('product')
        
        for item in items:
            # Get or create stock with lock
            stock, created = Stock.objects.select_for_update().get_or_create(
                product=item.product,
                defaults={'current_qty': 0}
            )
            
            if movement.movement_type == 'OUT':
                # Check sufficient stock (DISABLED - allow negative stock as per request)
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


class CheckoutService:
    """
    Toifa asosidagi chiqish (OUT) mantiqi.
    
    Mantiq zanjiri:
    1. Face ID → actor (Employee) aniqlanadi
    2. target_employee = actor YOKI boshqa xodim (komandir delegatsiya)
    3. actor == target YOKI actor.is_commander → ruxsat
    4. Standard: product.category in target.assigned_categories → OK
    5. Emergency: target.assigned_categories dagi barcha stock>0 mahsulotlar → bulk OUT
    """
    
    @staticmethod
    def _resolve_permission(actor: Employee, target: Employee):
        """
        Ruxsatni tekshirish.
        - actor == target → OK
        - actor == target.supervisor → OK (Komandir o'z xodimi uchun)
        - Aks holda → ValidationError
        """
        if actor.id == target.id:
            return  # O'z narsasini olayapti
        
        # Check if actor is the supervisor of the target
        if target.supervisor_id == actor.id:
            return  # Komandir o'z xodimi nomidan olyapti
            
        raise ValidationError(
            f"{actor.name} {target.name} ning rahbari (komandiri) emas."
        )
    
    @staticmethod
    @transaction.atomic
    def standard_checkout(actor: Employee, target: Employee, product, quantity: int, user):
        """
        Standart rejim: QR scan → egalik tekshiruvi → Face ID.
        
        Args:
            actor: Face ID orqali aniqlangan xodim.
            target: Mahsulot egasi bo'lgan xodim (actor yoki boshqa).
            product: QR skanerdan olingan Product instance.
            quantity: Chiqariladigan miqdor.
            user: Tizimga kirgan foydalanuvchi (Django User).
        
        Returns:
            Movement instance.
        """
        # 1. Ruxsat tekshiruvi (Actor vs Target)
        CheckoutService._resolve_permission(actor, target)
        
        # 2. Egalik tekshiruvi: Mahsulot target xodimga biriktirilganmi?
        if product.assigned_to_id != target.id:
            owner_name = product.assigned_to.name if product.assigned_to else "Hech kim"
            raise ValidationError(
                f"Bu mahsulot {target.name} ga biriktirilmagan. (Egasi: {owner_name})"
            )
        
        # 3. Zaxira tekshiruvi
        stock, _ = Stock.objects.select_for_update().get_or_create(
            product=product, defaults={'current_qty': 0}
        )
        
        # 4. Izoh tayyorlash
        if actor.id != target.id:
            note = f"Komandir {actor.name} → xodim {target.name} uchun chiqarish"
        else:
            note = "Standart chiqish"
        
        # 5. Movement yaratish
        movement = Movement.objects.create(
            movement_type='OUT',
            status='VERIFIED',
            performed_by=user,
            face_employee=actor,
            target_employee=target if actor.id != target.id else None,
            face_verified=True,
            face_confidence=1.0,
            face_verified_at=timezone.now(),
            is_emergency=False,
            note=note,
        )
        
        MovementItem.objects.create(
            movement=movement,
            product=product,
            quantity=quantity,
        )
        
        stock.current_qty -= quantity
        stock.save()
        
        return movement
    
    @staticmethod
    @transaction.atomic
    def emergency_checkout(actor: Employee, target: Employee, user):
        """
        Ekstrenniy rejim: Face ID → barcha biriktirilgan mahsulotlar bulk OUT.
        
        Args:
            actor: Face ID orqali aniqlangan xodim.
            target: Mahsulot egasi (actor yoki boshqa xodim).
            user: Tizimga kirgan foydalanuvchi.
        
        Returns:
            Movement instance.
        """
        # 1. Ruxsat tekshiruvi
        CheckoutService._resolve_permission(actor, target)
        
        # 2. Target ga biriktirilgan barcha stock > 0 mahsulotlarni topish
        stocks = Stock.objects.select_for_update().filter(
            product__assigned_to=target,
            current_qty__gt=0
        ).select_related('product')
        
        if not stocks.exists():
            raise ValidationError(
                f"{target.name} ga biriktirilgan mahsulotlar omborda qolmagan."
            )
        
        # 3. Izoh
        if actor.id != target.id:
            note = f"EKSTRENNIY: Komandir {actor.name} → xodim {target.name} uchun barchasini chiqarish"
        else:
            note = "EKSTRENNIY: Barchasini chiqarish"
        
        # 4. Movement yaratish
        movement = Movement.objects.create(
            movement_type='OUT',
            status='VERIFIED',
            performed_by=user,
            face_employee=actor,
            target_employee=target if actor.id != target.id else None,
            face_verified=True,
            face_confidence=1.0,
            face_verified_at=timezone.now(),
            is_emergency=True,
            note=note,
        )
        
        # 5. Har bir mahsulotni chiqarish
        for stock in stocks:
            MovementItem.objects.create(
                movement=movement,
                product=stock.product,
                quantity=stock.current_qty,
            )
            stock.current_qty = 0
            stock.save()
        
        return movement
