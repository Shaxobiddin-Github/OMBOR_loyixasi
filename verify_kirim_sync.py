
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
from inventory.models import Employee, Product, Category, Movement
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
    commander = create_unique_emp('Commander Ali Sync', True)
    subordinate = create_unique_emp('Subordinate Vali Sync', False, commander)
    
    # Subordinate's Product
    sku_sub = f"SKU_{uuid.uuid4().hex[:6]}"
    prod_sub = Product.objects.create(
        sku=sku_sub,
        name='Sub Product Sync',
        category=cat,
        assigned_to=subordinate,
        unit='dona',
        barcode=sku_sub
    )

    return user, commander, subordinate, prod_sub

def test_kirim_finalization(user, commander, subordinate, product):
    client = Client()
    client.force_login(user)
    
    print("--- 1. Testing Commander -> Subordinate Kirim Synchronization ---")

    # 1. Create Pending IN movement
    resp = client.post('/movement/create/', 
                       data=json.dumps({'movement_type': 'IN'}), 
                       content_type='application/json')
    if resp.status_code != 200:
        print(f"Setup Failed: Create Movement gave {resp.status_code}")
        return
    move_id = resp.json()['movement_id']

    # 2. Simulate Face Verification (Commander)
    session = client.session
    session['face_verified_employee_id'] = commander.id
    session['face_verified_user_id'] = user.id
    session['face_verified_station'] = '127.0.0.1'
    session['face_verified_at'] = timezone.now().isoformat()
    session['face_confidence'] = 0.95
    session.save()

    # 3. Add Item (Commander for Subordinate)
    resp = client.post(f'/movement/{move_id}/add-item/',
                       data=json.dumps({'product_id': product.id, 'quantity': 1}),
                       content_type='application/json')
    
    if resp.status_code != 200:
        print(f"Add Item Failed: {resp.status_code} {resp.content}")
        return

    # 4. Finalize Movement
    resp = client.post(f'/movement/{move_id}/finalize/')
    if resp.status_code != 200:
        print(f"Finalize Failed: {resp.status_code} {resp.content}")
        return
    
    print("Finalize Success.")

    # 5. Verify Database Records
    movement = Movement.objects.get(id=move_id)
    
    # Check Face Employee (Actor)
    if movement.face_employee == commander:
        print(f"✅ Face Employee saved correctly: {movement.face_employee.name}")
    else:
        print(f"❌ Face Employee incorrect. Got: {movement.face_employee}, Expected: {commander.name}")

    # Check Target Employee (Owner)
    if movement.target_employee == subordinate:
        print(f"✅ Target Employee saved correctly: {movement.target_employee.name}")
    else:
        print(f"❌ Target Employee incorrect. Got: {movement.target_employee}, Expected: {subordinate.name}")
    
    # Check Auto-Note
    expected_note = f"Komandir {commander.name} -> xodim {subordinate.name} uchun kirim"
    if expected_note in movement.note:
        print(f"✅ Auto-Note generated correctly: '{movement.note}'")
    else:
         print(f"❌ Auto-Note missing or incorrect. Got: '{movement.note}'")

if __name__ == '__main__':
    try:
        user, cmd, sub, prod = setup_data()
        test_kirim_finalization(user, cmd, sub, prod)
    except Exception as e:
        print(f"Error: {e}")
