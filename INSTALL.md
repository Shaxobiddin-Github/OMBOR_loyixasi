# Ombor Nazorat - O'rnatish Qo'llanmasi

Bu qo'llanma yangi kompyuterga loyihani noldan o'rnatishni tushuntiradi.

---

## 1-QADAM: Python O'rnatish

### Windows uchun:
1. https://www.python.org/downloads/ saytiga kiring
2. **Python 3.11** yoki undan yuqori versiyani yuklab oling
3. O'rnatish vaqtida **"Add Python to PATH"** ni belgilang ✅
4. O'rnating

### Tekshirish:
```bash
python --version
```
Natija: `Python 3.11.x` chiqishi kerak

---

## 2-QADAM: PostgreSQL O'rnatish

### Windows uchun:
1. https://www.postgresql.org/download/windows/ saytiga kiring
2. **PostgreSQL 15** yoki undan yuqori versiyani yuklab oling
3. O'rnatish vaqtida:
   - **Password:** eslab qoling (masalan: `123456`)
   - **Port:** `5432` (default)
4. O'rnating

### Bazani yaratish:
1. **pgAdmin** yoki **psql** ni oching
2. Yangi baza yarating:
```sql
CREATE DATABASE ombor_nazorat;
```

---

## 3-QADAM: Git O'rnatish

### Windows uchun:
1. https://git-scm.com/download/win saytiga kiring
2. Yuklab olib o'rnating
3. Tekshirish:
```bash
git --version
```

---

## 4-QADAM: Loyihani Klonlash

```bash
git clone https://github.com/Shaxobiddin-Github/OMBOR_loyixasi.git
cd OMBOR_loyixasi
```

---

## 5-QADAM: Virtual Muhit Yaratish

```bash
python -m venv env
```

### Windows da faollashtirish:
```bash
.\env\Scripts\activate
```

Faollashgandan keyin terminal boshida `(env)` yozuvi paydo bo'ladi.

---

## 6-QADAM: Kutubxonalarni O'rnatish

```bash
pip install -r requirements.txt
```

Bu quyidagilarni o'rnatadi:
- Django (web framework)
- psycopg2-binary (PostgreSQL driver)
- opencv-contrib-python (Face ID uchun)
- Pillow (rasm ishlash)
- openpyxl (Excel)
- xhtml2pdf (PDF)
- qrcode (QR kod)
- django-jazzmin (Admin dizayni)

---

## 7-QADAM: Sozlamalarni Tekshirish

`config/settings.py` faylini oching va baza sozlamalarini o'zgartiring:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ombor_nazorat',
        'USER': 'postgres',
        'PASSWORD': 'sizning_parolingiz',  # ← O'ZGARTIRING
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

### Backup sozlamasi (ixtiyoriy):
```python
PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"
```
Agar PostgreSQL boshqa joyda o'rnatilgan bo'lsa, yo'lni to'g'rilang.

---

## 8-QADAM: Bazani Migratsiya Qilish

```bash
python manage.py migrate
```

Bu barcha jadvallarni bazada yaratadi.

---

## 9-QADAM: Admin Foydalanuvchi Yaratish

```bash
python manage.py createsuperuser
```

So'ralgan ma'lumotlarni kiriting:
- **Username:** admin
- **Email:** admin@example.com
- **Password:** (kuchli parol)

---

## 10-QADAM: Serverni Ishga Tushirish

```bash
python manage.py runserver
```

Brauzerda oching:
- **Asosiy sayt:** http://127.0.0.1:8000/
- **Admin panel:** http://127.0.0.1:8000/admin/

---

## Qo'shimcha Qurilmalar

### Webcam (Face ID uchun)
- Har qanday USB webcam ishlaydi
- O'rnatishga hojat yo'q, avtomatik taniladi

### Shtrix Kod Skaneri
- **Talab:** HID Keyboard rejimini qo'llashi kerak
- Mashhur modellar: Honeywell, Zebra, Datalogic
- USB ga ulang - avtomatik ishlaydi
- Skaner skanerlasa → klaviatura yozgandek bo'ladi

---

## Mahalliy Tarmoqda Ishlatish (LAN)

Boshqa kompyuterlardan kirish uchun:

### 1. Serverni tashqi IP da ishga tushiring:
```bash
python manage.py runserver 0.0.0.0:8000
```

### 2. Firewall da 8000 portini oching

### 3. Boshqa kompyuterdan kiring:
```
http://192.168.1.100:8000/
```
(bu yerda `192.168.1.100` - server kompyuterning IP manzili)

---

## Xatoliklar va Yechimlar

| Xatolik | Yechim |
|---------|--------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` ni qayta ishga tushiring |
| `OperationalError: FATAL` | PostgreSQL ishlayotganini tekshiring, parolni to'g'rilang |
| `cv2 not found` | `pip install opencv-contrib-python` |
| `pg_dump version mismatch` | `PG_DUMP_PATH` ni server versiyasiga moslab o'zgartiring |

---

## To'liq O'rnatish Ketma-ketligi (Qisqacha)

```bash
# 1. Klonlash
git clone https://github.com/Shaxobiddin-Github/OMBOR_loyixasi.git
cd OMBOR_loyixasi

# 2. Virtual muhit
python -m venv env
.\env\Scripts\activate

# 3. Kutubxonalar
pip install -r requirements.txt

# 4. settings.py da baza parolini o'zgartiring

# 5. Migratsiya
python manage.py migrate

# 6. Admin yaratish
python manage.py createsuperuser

# 7. Ishga tushirish
python manage.py runserver
```

---

**Tayyor! Endi brauzerda http://127.0.0.1:8000/ ni oching va ishlang!**
