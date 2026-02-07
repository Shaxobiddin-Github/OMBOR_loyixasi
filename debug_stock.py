
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventory.models import Product, Stock, MovementItem

def analyze_coca_cola():
    print("--- Detailed Analysis of Coca-Cola ---")
    
    # Check all products
    products = Product.objects.filter(name__icontains='Cola')
    print(f"Products found: {products.count()}")
    
    for p in products:
        print(f"\nPRODUCT: {p.name} (ID: {p.id})")
        print(f"  SKU: {p.sku}")
        print(f"  Barcode: {p.barcode}")
        print(f"  Min Stock: {p.min_stock}")
        
        # Stock
        try:
            stock = Stock.objects.get(product=p)
            print(f"  STOCK Qty: {stock.current_qty}")
        except Stock.DoesNotExist:
            print(f"  STOCK: Missing!")
            
        # Movements
        items = MovementItem.objects.filter(product=p)
        print(f"  MOVEMENT ITEMS: {items.count()}")
        for item in items:
            mov = item.movement
            print(f"    - Mov #{mov.id} ({mov.movement_type}): {item.quantity} qty | Status: {mov.status}")
            
if __name__ == '__main__':
    analyze_coca_cola()
