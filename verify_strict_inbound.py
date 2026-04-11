
import os
import django
import json
import sys
import uuid
import random

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from inventory.models import Employee, Product, Category
from django.utils import timezone

User = get_user_model()

def setup_data():
    # Create User
    user, _ = User.objects.get_or_create(username='test_operator', role='operator')
    user.set_password('pass')
    user.save()

    # Create Category
    cat, _ = Category.objects.get_or_create(name='Test Cat')

    # Helper to create unique employee
    def create_unique_emp(name, is_cmd=False, sup=None):
        while True:
            label = random.randint(1000, 9999)
            if not Employee.objects.filter(face_label=label).exists():
                break
        
        eid = f"TEST_{uuid.uuid4().hex[:6].upper()}"
        return Employee.objects.create(
            employee_id=eid,
            name=name,
            face_label=label,
            is_commander=is_cmd,
            supervisor=sup
        )

    # Create Employees
    commander = create_unique_emp('Commander Ali', True)
    subordinate = create_unique_emp('Subordinate Vali', False, commander)
    regular = create_unique_emp('Regular Gani', False)

    # Create Products with Unique SKUs
    # Subordinate's Product
    sku_sub = f"SKU_{uuid.uuid4().hex[:6]}"
    prod_sub = Product.objects.create(
        sku=sku_sub,
        name='Sub Product',
        category=cat,
        assigned_to=subordinate,
        unit='dona',
        barcode=sku_sub
    )

    # Regular's Product
    sku_reg = f"SKU_{uuid.uuid4().hex[:6]}"
    prod_reg = Product.objects.create(
        sku=sku_reg,
        name='Reg Product',
        category=cat,
        assigned_to=regular,
        unit='dona',
        barcode=sku_reg
    )

    return user, commander, subordinate, regular, prod_sub, prod_reg

def test_permission(user, actor, product, expected_success, message_tag):
    client = Client()
    client.force_login(user)
    
    # 1. Create Pending IN movement
    resp = client.post('/movement/create/', 
                       data=json.dumps({'movement_type': 'IN'}), 
                       content_type='application/json')
    if resp.status_code != 200:
        print(f"[{message_tag}] Setup Failed: Create Movement gave {resp.status_code}")
        return
    
    try:
        move_id = resp.json()['movement_id']
    except:
         print(f"[{message_tag}] Setup Failed: No movement_id in {resp.json()}")
         return

    # 2. Simulate Face Verification in Session
    session = client.session
    session['face_verified_employee_id'] = actor.id
    session['face_verified_user_id'] = user.id
    session['face_verified_station'] = '127.0.0.1'
    session['face_verified_at'] = timezone.now().isoformat()
    session.save()

    # 3. Add Item
    resp = client.post(f'/movement/{move_id}/add-item/',
                       data=json.dumps({'product_id': product.id, 'quantity': 1}),
                       content_type='application/json')
    
    success = resp.status_code == 200 and resp.json().get('ok')
    
    result = "PASS" if success == expected_success else "FAIL"
    print(f"[{message_tag}] Actor: {actor.name}, ProductOwner: {product.assigned_to.name} -> Expect: {'Success' if expected_success else 'Fail'} | Got: {resp.status_code} {resp.json() if resp.content else ''} -> {result}")

def run_tests():
    try:
        user, cmd, sub, reg, prod_sub, prod_reg = setup_data()
        print("Data Setup Complete.")
        
        # Test 1: Commander acting for Subordinate (Should Pass)
        test_permission(user, cmd, prod_sub, True, "CMD->SUB")
        
        # Test 2: Regular acting for Subordinate (Should Fail)
        test_permission(user, reg, prod_sub, False, "REG->SUB")
        
        # Test 3: Regular acting for Self (Should Pass)
        test_permission(user, reg, prod_reg, True, "REG->SELF")
        
        # Test 4: Commander acting for Self (Should Pass)
        # Assign prod to Commander with unique SKU
        sku_cmd = f"SKU_{uuid.uuid4().hex[:6]}"
        prod_cmd = Product.objects.create(
            sku=sku_cmd,
            name='Cmd Product',
            category=prod_sub.category,
            assigned_to=cmd,
            unit='dona',
            barcode=sku_cmd
        )
        test_permission(user, cmd, prod_cmd, True, "CMD->SELF")

        # Test 5: Subordinate acting for Commander (Should Fail)
        test_permission(user, sub, prod_cmd, False, "SUB->CMD")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run_tests()
