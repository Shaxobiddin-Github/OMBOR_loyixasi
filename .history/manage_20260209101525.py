#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from tendo import singleton  # <--- 1. Importni shu yerga qo'shasiz

def main():
    # --- 2. TEKSHIRUV KODINI SHU YERGA (FUNKSIYA BOSHIGA) QO'YASIZ ---
    try:
        # Bu qator dastur faqat bitta nusxada ishlashini ta'minlaydi
        me = singleton.SingleInstance()
    except singleton.SingleInstanceException:
        # Agar allaqachon ishlab turgan bo'lsa, jimgina yopiladi
        sys.exit(0) 
    # -----------------------------------------------------------------

    """Run administrative tasks."""
    # O'zingizning loyiha nomingizni tekshirib oling (masalan: 'config.settings')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sizning_loyihangiz.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()