import os
import sys
from waitress import serve

# --------------------------------------------------------------
# ENG MUHIM QISM: Probel bor papkalarni to'g'ri topish
# --------------------------------------------------------------
# Hozirgi fayl turgan papkani aniqlaymiz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Tizim yo'liga qo'shamiz (Python "config" papkasini ko'rishi uchun)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# --------------------------------------------------------------
# Django sozlamalari
# --------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from config.wsgi import application
except ImportError as e:
    # Agar xato bo'lsa, logga yozib qo'yamiz (debug uchun)
    with open(os.path.join(BASE_DIR, 'startup_error.txt'), 'w') as f:
        f.write(f"Import Error: {e}")
    raise e

if __name__ == "__main__":
    # Host 0.0.0.0 bo'lsa, tarmoqda ham ishlaydi
    serve(application, host="0.0.0.0", port=8000, threads=4)