#!/usr/bin/env python
import os
import sys
import socket  # <--- Tendo o'rniga Socket ishlatamiz

# --- YAGONA NUSXA TEKSHIRUVI ---
def check_single_instance():
    # Bu port raqamini (masalan, 55555) o'zingiz xohlagan songa o'zgartirishingiz mumkin.
    # Lekin loyihangiz uchun bir xil bo'lishi kerak.
    port_id = 55555 
    
    # Global o'zgaruvchi qilish shart emas, chunki socket obyekti 
    # dastur yopilguncha "bind" holatida turadi.
    global s  
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 127.0.0.1 (localhost) da portni band qilamiz
        s.bind(("127.0.0.1", port_id))
    except socket.error:
        # Agar port band bo'lsa, demak dastur allaqachon ishlayapti
        print("Dastur allaqachon ishga tushirilgan!")
        sys.exit(0)
# -------------------------------

def main():
    # Tekshiruv funksiyasini chaqiramiz
    check_single_instance()

    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ombor_nazorat.settings') # <-- Loyiha nomini tekshiring
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