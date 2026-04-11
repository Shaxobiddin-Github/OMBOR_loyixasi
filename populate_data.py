
# import os
# import django
# import random
# from decimal import Decimal

# # Set up Django environment
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()

# from django.contrib.auth import get_user_model
# from inventory.models import Category, Product, Employee, Stock, Movement, MovementItem

# User = get_user_model()

# def create_users():
#     print("Creating users...")
#     admin, created = User.objects.get_or_create(username='admin', defaults={'role': 'admin', 'email': 'admin@example.com'})
#     if created:
#         admin.set_password('admin123')
#         admin.save()
#         print(f"User {admin.username} created.")
#     else:
#         print(f"User {admin.username} already exists.")

#     operator, created = User.objects.get_or_create(username='operator', defaults={'role': 'operator', 'email': 'operator@example.com'})
#     if created:
#         operator.set_password('operator123')
#         operator.save()
#         print(f"User {operator.username} created.")
#     else:
#         print(f"User {operator.username} already exists.")

#     viewer, created = User.objects.get_or_create(username='viewer', defaults={'role': 'viewer', 'email': 'viewer@example.com'})
#     if created:
#         viewer.set_password('viewer123')
#         viewer.save()
#         print(f"User {viewer.username} created.")
#     else:
#         print(f"User {viewer.username} already exists.")
    
#     return admin, operator

# def create_employees():
#     print("Creating employees...")
#     employees = []
#     names = ['Ali Valiyev', 'Vali Aliyev', 'Gani Teshayev']
#     for i, name in enumerate(names):
#         employee, created = Employee.objects.get_or_create(
#             employee_id=f'EMP{i+1:03d}',
#             defaults={
#                 'name': name,
#                 'face_label': i+1,
#                 'is_active': True
#             }
#         )
#         if created:
#             print(f"Employee {employee.name} created.")
#         else:
#             print(f"Employee {employee.name} already exists.")
#         employees.append(employee)
#     return employees

# def create_categories():
#     print("Creating categories...")
#     categories = []
#     cats = ['Elektronika', 'Maishiy texnika', 'Mebel', 'Kiyim-kechak', 'Oziq-ovqat']
#     for name in cats:
#         category, created = Category.objects.get_or_create(name=name)
#         if created:
#             print(f"Category {category.name} created.")
#         categories.append(category)
#     return categories

# def create_products(categories):
#     print("Creating products...")
#     products = []
#     # (name, category_index, sku, barcode, unit, min_stock)
#     prod_data = [
#         ('Laptop HP Pavilion', 0, 'LAP-001', '1234567890123', 'dona', 5),
#         ('iPhone 13', 0, 'PHN-001', '1234567890124', 'dona', 10),
#         ('Samsung TV 55"', 1, 'TV-001', '1234567890125', 'dona', 3),
#         ('Kreslo Ofis', 2, 'FUR-001', '1234567890126', 'dona', 20),
#         ('Erkaklar Futbolkasi', 3, 'CLT-001', '1234567890127', 'dona', 50),
#         ('Olma (Red Chief)', 4, 'FUD-001', '1234567890128', 'kg', 100),
#     ]

#     for name, cat_idx, sku, barcode, unit, min_stock in prod_data:
#         category = categories[cat_idx]
#         product, created = Product.objects.get_or_create(
#             sku=sku,
#             defaults={
#                 'name': name,
#                 'category': category,
#                 'barcode': barcode,
#                 'unit': unit,
#                 'min_stock': min_stock,
#                 'description': f"Test product: {name}"
#             }
#         )
#         if created:
#             print(f"Product {product.name} created.")
#         else:
#             print(f"Product {product.name} already exists.")
#         products.append(product)
#     return products

# def content_stock(admin, products):
#     print("Creating initial stock via 'IN' movements...")
    
#     # Create one IN movement
#     movement = Movement.objects.create(
#         movement_type='IN',
#         status='VERIFIED', # Auto-verify for test data
#         performed_by=admin,
#         note='Initial stock population'
#     )
    
#     for product in products:
#         qty = random.randint(10, 100)
#         price = Decimal(random.randint(10000, 5000000))
        
#         MovementItem.objects.create(
#             movement=movement,
#             product=product,
#             quantity=qty,
#             unit_price=price
#         )
        
#         # Manually update stock as signal might only create it but not update quantity if logic is specific
#         # But wait, Stock is created by signal? 
#         # Usually Stock model is updated via signals on Movement verification or manually in views.
#         # Let's check if the project has signals to update stock on movement verification.
#         # I'll update stock manually here to be sure.
        
#         stock, _ = Stock.objects.get_or_create(product=product)
#         stock.current_qty += qty
#         stock.save()
        
#         print(f"Added {qty} {product.unit} of {product.name} to stock.")

# def assign_portfolios(employees, products):
#     print("Assigning portfolios and roles...")
    
#     # Ali Valiyev - Commander
#     ali = employees[0]
#     ali.is_commander = True
#     ali.save()
#     print(f"Employee {ali.name} set as Commander.")
    
#     # Assign Laptop to Ali
#     # Assuming products[0] is Laptop
#     laptop = products[0]
#     EmployeeProduct.objects.get_or_create(employee=ali, product=laptop, defaults={'quantity': 1})
#     print(f"Assigned {laptop.name} to {ali.name}")
    
#     # Assign Phone to Vali
#     vali = employees[1]
#     phone = products[1]
#     EmployeeProduct.objects.get_or_create(employee=vali, product=phone, defaults={'quantity': 1})
#     print(f"Assigned {phone.name} to {vali.name}")

# if __name__ == '__main__':
#     admin, operator = create_users()
#     employees = create_employees()
#     categories = create_categories()
#     products = create_products(categories)
#     content_stock(admin, products)
#     assign_portfolios(employees, products)
#     print("Database population completed successfully!")
