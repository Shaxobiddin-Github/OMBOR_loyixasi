import os
import sys
from waitress import serve

# 1. Loyiha papkasini tizim yo'liga qo'shamiz (Service adashmasligi uchun)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# 2. Sozlamalarni ko'rsatamiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 3. Ilovani yuklaymiz
from config.wsgi import application

if __name__ == "__main__":
    print(f"Server ishga tushmoqda: {BASE_DIR}")
    # host="0.0.0.0" qilsangiz, tarmoqdagi boshqa kompyuterlar ham kira oladi.
    # Agar faqat shu kompyuter uchun bo'lsa "127.0.0.1" qolaversin.
    serve(application, host="0.0.0.0", port=8000, threads=4)