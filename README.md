# Ombor Nazorat - Warehouse Management System

Local (offline) warehouse inventory control system with Face ID verification.

## Tech Stack

- **Backend**: Python 3.11, Django 4.2
- **Database**: PostgreSQL
- **Face ID**: OpenCV LBPH (opencv-contrib-python)
- **Frontend**: Django Templates, Vanilla CSS/JS
- **QR Scanner**: HID Keyboard Mode

## Features

- ✅ Role-based access (Admin/Operator/Viewer)
- ✅ Face ID verification on all movements
- ✅ QR/Barcode scanner integration
- ✅ Atomic stock updates with locking
- ✅ Movement reversal (no deletion)
- ✅ Database backup & download
- ✅ Dark mode UI
- ✅ Works 100% offline

---

## Windows Setup

### 1. Prerequisites

1. **Python 3.11+**
   ```
   winget install Python.Python.3.11
   ```

2. **PostgreSQL 15+**
   ```
   winget install PostgreSQL.PostgreSQL
   ```
   
   After installation, add to PATH:
   ```
   C:\Program Files\PostgreSQL\15\bin
   ```

3. **Git** (optional)
   ```
   winget install Git.Git
   ```

### 2. Create Database

Open **pgAdmin** or **psql** and run:

```sql
CREATE DATABASE ombor_nazorat;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE ombor_nazorat TO postgres;
```

Or via command line:
```cmd
psql -U postgres -c "CREATE DATABASE ombor_nazorat;"
```

### 3. Setup Project

```cmd
cd d:\project\ombor_nazorat

:: Create virtual environment
python -m venv venv
venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt
```

### 4. Configure Settings

Edit `config/settings.py` if needed:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ombor_nazorat',
        'USER': 'postgres',
        'PASSWORD': 'your_password',  # Change this!
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# If pg_dump is not in PATH:
PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"
```

### 5. Run Migrations

```cmd
python manage.py makemigrations accounts
python manage.py makemigrations inventory
python manage.py migrate
```

### 6. Create Admin User

```cmd
python manage.py createsuperuser
```

When prompted, enter:
- Username: `admin`
- Email: (optional)
- Password: your choice
- Role will be set via admin panel

### 7. Set User Roles

1. Go to Django Admin: `http://127.0.0.1:8000/admin/`
2. Navigate to **Accounts > Users**
3. Edit user and set **Role** to `admin`

### 8. Add Test Data (Optional)

1. Go to Admin panel
2. Add **Categories** (e.g., Elektronika, Oziq-ovqat)
3. Add **Products** with unique barcodes
4. Add **Employees** with unique `face_label` (1, 2, 3...)

### 9. Register Face IDs

1. Go to **Xodimlar** page
2. Click on employee → **Face ID**
3. Capture 10-30 photos
4. Click **Ro'yxatga olish**

### 10. Run Server

```cmd
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## Usage

### Kirim (IN)

1. Login as Operator or Admin
2. Click **Kirim** in sidebar
3. Scan QR code or type barcode + Enter
4. Enter quantity
5. Click **📸 Tasdiqlash** for Face ID
6. Click **✅ Yakunlash** to complete

### Chiqim (OUT)

Same as Kirim, but checks available stock.

### Reversal (Admin only)

1. Go to **Harakatlar**
2. Click on VERIFIED movement
3. Click **🔄 Bekor qilish**
4. Enter reason

### Backup

```cmd
python manage.py backup_db
```

Or download via Admin panel.

---

## QR Scanner Setup

1. Connect USB barcode/QR scanner
2. Set scanner to **HID Keyboard Mode** (default for most scanners)
3. Scanner should add Enter after scan (check scanner manual)
4. Focus on QR input field → scan → product auto-added

---

## File Structure

```
ombor_nazorat/
├── manage.py
├── requirements.txt
├── README.md
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/
│   ├── models.py      (User model with roles)
│   ├── views.py       (Login/logout)
│   └── decorators.py  (Role permissions)
├── inventory/
│   ├── models.py      (Employee, Product, Stock, Movement)
│   ├── views.py       (All endpoints)
│   ├── services.py    (StockService)
│   ├── face_service.py (OpenCV LBPH)
│   └── management/commands/backup_db.py
├── templates/
├── static/
├── media/
│   └── face_models/   (model.yml stored here)
└── backups/           (SQL backups)
```

---

## Troubleshooting

### "opencv-contrib-python not found"
```cmd
pip uninstall opencv-python opencv-contrib-python
pip install opencv-contrib-python
```

### "pg_dump not found"
Set `PG_DUMP_PATH` in settings.py:
```python
PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"
```

### Camera not working
- Check browser permissions for camera
- Try different browser (Chrome recommended)
- Check if camera is in use by another app

### Face not recognized
- Ensure good lighting
- Re-register with more (20+) photos
- Face should be centered in camera

---

## License

Internal use only.
