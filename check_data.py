
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventory.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

print("--- Users ---")
for u in User.objects.all():
    print(f"User: {u.username}, Role: {u.role}")

print("\n--- Employees ---")
for e in Employee.objects.all():
    print(f"Employee: {e.name} (ID: {e.employee_id}), Commander: {e.is_commander}")
