
import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventory.models import Employee
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    print("User Model:", User)
    
    print("\n--- User Fields ---")
    for f in User._meta.get_fields():
        print(f"{f.name} ({f.__class__.__name__})")

    print("\n--- Employee Fields ---")
    for f in Employee._meta.get_fields():
        print(f"{f.name} ({f.__class__.__name__})")
        
except Exception as e:
    print(f"Error: {e}")
