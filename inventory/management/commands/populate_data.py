"""
Populate database with test data.
Handles existing data gracefully.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import IntegrityError
from inventory.models import Category, Product, Employee, Stock, Movement, MovementItem
from accounts.models import User
import random

class Command(BaseCommand):
    help = 'Populate database with test data'

    def handle(self, *args, **options):
        self.stdout.write("Test ma'lumotlari yaratilmoqda...")
        
        # 1. Categories
        categories = ['Elektronika', 'Maishiy texnika', 'Oziq-ovqat', 'Kiyim-kechak', 'Qurilish mollari']
        cat_objs = {}
        for name in categories:
            cat, created = Category.objects.get_or_create(name=name)
            cat_objs[name] = cat
            if created:
                self.stdout.write(f"Kategoriya yaratildi: {name}")

        # 2. Products
        products_data = [
            # Elektronika
            {'name': 'iPhone 15 Pro 128GB', 'sku': 'IPH15-128', 'barcode': '195949042456', 'cat': 'Elektronika', 'unit': 'dona', 'min': 5},
            {'name': 'Samsung Galaxy S24 Ultra', 'sku': 'S24U-256', 'barcode': '880609459234', 'cat': 'Elektronika', 'unit': 'dona', 'min': 3},
            # ... kept brief for stability, add more if needed
        ]
        
        # Add more products if needed, but let's stick to core ones to ensure success first
        more_products = [
             {'name': 'MacBook Pro 14 M3', 'sku': 'MBP14-M3', 'barcode': '194253456789', 'cat': 'Elektronika', 'unit': 'dona', 'min': 2},
             {'name': 'Coca-Cola 1.5L', 'sku': 'COLA-15', 'barcode': '5449000000996', 'cat': 'Oziq-ovqat', 'unit': 'dona', 'min': 50},
        ]
        products_data.extend(more_products)

        created_products = []
        for p in products_data:
            try:
                prod, created = Product.objects.get_or_create(
                    barcode=p['barcode'],
                    defaults={
                        'name': p['name'],
                        'sku': p['sku'],
                        'category': cat_objs[p['cat']],
                        'unit': p['unit'],
                        'min_stock': p['min']
                    }
                )
                created_products.append(prod)
                if created:
                    self.stdout.write(f"Mahsulot yaratildi: {prod.name}")
            except IntegrityError:
                self.stdout.write(f"Mahsulot mavjud (sku/barcode conflict): {p['name']}")
                # Try fetching by barcode if get_or_create failed weirdly, or just skip
                continue

        # 3. Employees
        employees_data = [
            {'name': 'Ali Valiyev', 'id': 'EMP001'},
            {'name': 'Vali G\'aniyev', 'id': 'EMP002'},
            {'name': 'Salim Karimov', 'id': 'EMP003'},
        ]

        created_employees = []
        
        # Determine next available face_label
        used_labels = set(Employee.objects.values_list('face_label', flat=True))
        msg_label = 1
        
        for e in employees_data:
            # Check if exists by ID
            emp = Employee.objects.filter(employee_id=e['id']).first()
            if not emp:
                # Find valid label
                while msg_label in used_labels:
                    msg_label += 1
                
                emp = Employee.objects.create(
                    employee_id=e['id'],
                    name=e['name'],
                    face_label=msg_label,
                    is_active=True
                )
                used_labels.add(msg_label)
                self.stdout.write(f"Xodim yaratildi: {emp.name} (Label: {msg_label})")
            else:
                self.stdout.write(f"Xodim mavjud: {emp.name}")
            
            created_employees.append(emp)

        # 4. Stock & Movements
        admin = User.objects.filter(role='admin').first()
        if not admin:
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin')

        # Check if we have verified in movements
        if not Movement.objects.filter(movement_type='IN', status='VERIFIED').exists():
            self.stdout.write("Boshlang'ich zaxira yaratilmoqda...")
            
            movement = Movement.objects.create(
                movement_type='IN',
                status='VERIFIED',
                performed_by=admin,
                face_employee=created_employees[0],
                face_verified=True,
                face_verified_at=timezone.now(),
                created_at=timezone.now(),
                note="Avto test ma'lumotlari"
            )

            for prod in created_products:
                qty = random.randint(50, 200)
                price = random.randint(1000, 100000)
                
                MovementItem.objects.create(
                    movement=movement,
                    product=prod,
                    quantity=qty,
                    unit_price=price
                )
                
                if hasattr(prod, 'stock') and prod.stock:
                    prod.stock.current_qty += qty
                    prod.stock.save()

            self.stdout.write("✅ Zaxira yangilandi")

        self.stdout.write(self.style.SUCCESS("TAYYOR!"))
