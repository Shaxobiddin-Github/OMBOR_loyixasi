import os
import django
from django.core.exceptions import ValidationError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import Employee, Product, Movement, MovementItem, Stock
from inventory.services import StockService

User = get_user_model()

def test_inbound():
    admin = User.objects.get(username='admin')
    ali  = Employee.objects.get(employee_id='EMP001')  # Commander
    vali = Employee.objects.get(employee_id='EMP002')  # Subordinate of Ali
    gani = Employee.objects.get(employee_id='EMP003')  # Independent

    laptop = Product.objects.get(sku='LAP-001')  # Assigned to Ali
    shirt  = Product.objects.get(sku='CLT-001')  # Assigned to Vali
    tv     = Product.objects.get(sku='TV-001')   # Assigned to Gani

    print("=== TEST INBOUND LOGIC ===")

    # 1. SETUP: Ensure hierarchy
    if vali.supervisor != ali:
        vali.supervisor = ali
        vali.save()
        print("Set Ali as supervisor of Vali")

    # ─────────────────────────────────────────────
    # Test 1: Standard IN - Vali brings his own Shirt
    # ─────────────────────────────────────────────
    print("\nTest 1: Vali brings Shirt (Own Item)")
    
    # Create Movement
    mov1 = Movement.objects.create(
        movement_type='IN',
        status='PENDING',
        performed_by=admin,
        target_employee=vali, # Target is Vali
        note="Vali inbound"
    )
    
    # Add Item (Should succeed as Shirt is assigned to Vali)
    item1 = MovementItem.objects.create(movement=mov1, product=shirt, quantity=5)
    print("  ✅ Item added to pending movement")

    # Finalize (Face ID: Vali)
    try:
        StockService.process_movement(mov1, vali.id, 0.99)
        print("  ✅ Finalized successfully by Vali")
    except ValidationError as e:
        print(f"  ❌ FAIL Finalize: {e}")

    # ─────────────────────────────────────────────
    # Test 2: Supervisor IN - Ali brings Vali's Shirt
    # ─────────────────────────────────────────────
    print("\nTest 2: Ali brings Shirt (Vali's Item - Delegation)")
    
    mov2 = Movement.objects.create(
        movement_type='IN',
        status='PENDING',
        performed_by=admin,
        target_employee=vali, # Target is STILL Vali (Owner)
        note="Ali bringing for Vali"
    )
    
    # Add Item (Succeeds because product.assigned_to == movement.target_employee)
    item2 = MovementItem.objects.create(movement=mov2, product=shirt, quantity=3)
    print("  ✅ Item added")

    # Finalize (Face ID: Ali - Supervisor)
    try:
        StockService.process_movement(mov2, ali.id, 0.99)
        print("  ✅ Finalized successfully by Supervisor Ali")
    except ValidationError as e:
        print(f"  ❌ FAIL Finalize: {e}")

    # ─────────────────────────────────────────────
    # Test 3: Unauthorized IN - Vali tries to bring Ali's Laptop (as Owner?)
    # ─────────────────────────────────────────────
    print("\nTest 3: Vali tries to bring Laptop (Ali's Item)")
    
    # Case A: Vali claims HE is the target (Misleading)
    # create_movement with target=Vali
    mov3 = Movement.objects.create(
        movement_type='IN',
        status='PENDING',
        performed_by=admin,
        target_employee=vali
    )
    
    # Add Item: Laptop (Assigned to Ali) -> Should FAIL at `add_movement_item` logic
    # But here we test Service/Logic manually.
    # Logic in views.py `add_movement_item` checks: product.assigned_to == movement.target
    if laptop.assigned_to == mov3.target_employee:
         print("  ❌ Logic Error: Laptop should not match Vali")
    else:
         print("  ✅ Views Logic would block this: Laptop assigned to Ali != Target Vali")

    # Case B: Vali claims target is Ali (Correct Owner), but Vali is NOT supervisor
    mov4 = Movement.objects.create(
        movement_type='IN',
        status='PENDING',
        performed_by=admin,
        target_employee=ali # Target is Ali
    )
    MovementItem.objects.create(movement=mov4, product=laptop, quantity=1)
    
    # Finalize by Vali
    try:
        StockService.process_movement(mov4, vali.id, 0.99)
        print("  ❌ FAIL: Vali should NOT be able to finalize for Ali")
    except ValidationError as e:
        print(f"  ✅ SUCCESS: Caught unauthorized access: {e}")

if __name__ == '__main__':
    test_inbound()
