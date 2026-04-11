import os

path = r"d:\project\ombor_nazorat\templates\inventory\movement_form.html"

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Specific replacements for the known corrupted patterns
    # We target the specific fields to avoid accidental global replacements in JS logic if any exists (though unlikely)
    fixes = [
        ('{ { item.id } }', '{{ item.id }}'),
        ('{ { item.product.id } }', '{{ item.product.id }}'),
        ('{ { item.quantity } }', '{{ item.quantity }}'),
        ('{ { item.product.stock.current_qty |default: 0 } }', '{{ item.product.stock.current_qty|default:0 }}'),
        # These seemed okay in view but let's be safe
        ('{ { item.product.name|escapejs } }', '{{ item.product.name|escapejs }}'),
        ('{ { item.product.sku|escapejs } }', '{{ item.product.sku|escapejs }}'),
        ('{ { item.product.unit|escapejs } }', '{{ item.product.unit|escapejs }}') 
    ]

    new_content = content
    count = 0
    for bad, good in fixes:
        if bad in new_content:
            new_content = new_content.replace(bad, good)
            count += 1
            
    # Also generic replacement if specific ones missed (e.g. whitespace variations)
    # Regex is better but simple replace is safer for now if we verify.
    # Let's clean up the block specifically.
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"Successfully applied {count} replacements to {path}")

except Exception as e:
    print(f"Error: {e}")
