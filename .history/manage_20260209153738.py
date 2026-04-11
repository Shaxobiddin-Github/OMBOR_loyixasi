#!/usr/bin/env python
import os
import sys
import socket

# --- YAGONA NUSXA TEKSHIRUVI ---
def check_single_instance():
    # 55555 port orqali dastur faqat bitta nusxada ishlashini ta'minlaymiz
    port_id = 55555 
    global s  
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port_id))
    except socket.error:
        # Agar port band bo'lsa, demak dastur allaqachon ishlab turibdi
        sys.exit(0)
# -------------------------------

def main():
    # Tekshiruv funksiyasini chaqiramiz
    check_single_instance()

    """Administrative vazifalarni bajarish."""
    
    # DIQQAT: Sizda settings.py 'config' papkasida, shuning uchun 'config.settings' bo'ladi
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings') 
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django topilmadi. Virtual muhit (env) faol ekanligiga ishonch hosil qiling."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()