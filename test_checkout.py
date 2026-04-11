import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from inventory.models import Employee, Product, Stock
from inventory.services import CheckoutService

User = get_user_model()


def test():
    admin = User.objects.get(username='admin')
    ali  = Employee.objects.get(employee_id='EMP001')  # Commander
    vali = Employee.objects.get(employee_id='EMP002')  # Subordinate of Ali
    gani = Employee.objects.get(employee_id='EMP003')  # Independent

    laptop = Product.objects.get(sku='LAP-001')
    shirt  = Product.objects.get(sku='CLT-001')
    tv     = Product.objects.get(sku='TV-001')

    # ─────────────────────────────────────────────
    # SETUP: Yangi "Assigned To" va "Supervisor" logikasini o'rnatish
    # ─────────────────────────────────────────────
    print("SETUP: Configuring assignments and hierarchy...")
    
    # 1. Ierarxiya: Ali -> Vali
    vali.supervisor = ali
    vali.save()
    print(f"  - {vali.name} ning rahbari: {ali.name}")

    # 2. Tovarlarni biriktirish
    # Laptop -> Ali
    laptop.assigned_to = ali
    laptop.save()
    print(f"  - {laptop.name} biriktirildi: {ali.name}")

    # Shirt -> Vali
    shirt.assigned_to = vali
    shirt.save()
    print(f"  - {shirt.name} biriktirildi: {vali.name}")

    # TV -> Gani
    tv.assigned_to = gani
    tv.save()
    print(f"  - {tv.name} biriktirildi: {gani.name}")
    print("-" * 50)

    # ─────────────────────────────────────────────
    # Test 1: STANDART — Vali o'ziga biriktirilgan tovarni oladi
    # ─────────────────────────────────────────────
    print("Test 1: Vali takes Shirt (Assigned to VALI)")
    try:
        m = CheckoutService.standard_checkout(vali, vali, shirt, 1, admin)
        print(f"  ✅ SUCCESS — Movement #{m.id}\n")
    except ValidationError as e:
        print(f"  ❌ FAIL: {e}\n")

    # ─────────────────────────────────────────────
    # Test 2: STANDART — Vali Ali ning tovarini olmoqchi -> FAIL
    # ─────────────────────────────────────────────
    print("Test 2: Vali takes Laptop (Assigned to ALI) -> Should FAIL")
    try:
        CheckoutService.standard_checkout(vali, vali, laptop, 1, admin)
        print("  ❌ FAIL: Should have raised error\n")
    except ValidationError as e:
        print(f"  ✅ SUCCESS — Caught: {e}\n")

    # ─────────────────────────────────────────────
    # Test 3: STANDART — Ali o'z tovarini oladi
    # ─────────────────────────────────────────────
    print("Test 3: Ali takes Laptop (Assigned to ALI)")
    try:
        m = CheckoutService.standard_checkout(ali, ali, laptop, 1, admin)
        print(f"  ✅ SUCCESS — Movement #{m.id}\n")
    except ValidationError as e:
        print(f"  ❌ FAIL: {e}\n")

    # ─────────────────────────────────────────────
    # Test 4: KOMANDIR DELEGATSIYA — Ali (Supervisor), Vali ning tovarini oladi
    # ─────────────────────────────────────────────
    print("Test 4: Supervisor Ali takes Shirt (Assigned to VALI)")
    try:
        m = CheckoutService.standard_checkout(ali, vali, shirt, 1, admin)
        print(f"  ✅ SUCCESS — Movement #{m.id}, target={m.target_employee}\n")
    except ValidationError as e:
        print(f"  ❌ FAIL: {e}\n")

    # ─────────────────────────────────────────────
    # Test 5: DELEGATSIYA RUXSATSIZ — Vali, Ali uchun olmoqchi → FAIL
    # ─────────────────────────────────────────────
    print("Test 5: Subordinate Vali tries to take FOR Ali -> Should FAIL")
    try:
        CheckoutService.standard_checkout(vali, ali, laptop, 1, admin)
        print("  ❌ FAIL: Should have raised error\n")
    except ValidationError as e:
        print(f"  ✅ SUCCESS — Caught: {e}\n")
    
    # ─────────────────────────────────────────────
    # Test 6: Begona — Ali, Gani ning tovarini olmoqchi (Gani Ali ga bo'ysunmaydi) -> FAIL
    # ─────────────────────────────────────────────
    print("Test 6: Ali tries to take TV (Assigned to GANI) -> Should FAIL (Not supervisor)")
    try:
        CheckoutService.standard_checkout(ali, gani, tv, 1, admin)
        print("  ❌ FAIL: Should have raised error\n")
    except ValidationError as e:
        print(f"  ✅ SUCCESS — Caught: {e}\n")


if __name__ == '__main__':
    test()
