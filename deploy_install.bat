@echo off
cls
echo =======================================
echo TIZIM VA BAZANI SOZLASH BOSHLANDI...
echo =======================================

pushd "%~dp0"
set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

:: ---------------------------------------------------------
:: 1. POSTGRESQL MANZILINI TOPISH VA BAZA YARATISH
:: ---------------------------------------------------------
echo.
echo [1/4] PostgreSQL o'rnatilgan manzil qidirilmoqda...

set "PG_BIN="
:: 18 dan 13 gacha bo'lgan barcha versiyalarni tekshirib chiqadi
for /L %%V in (18,-1,13) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        set "PG_BIN=C:\Program Files\PostgreSQL\%%V\bin"
        echo PostgreSQL %%V versiyasi topildi!
        goto :found_pg
    )
)

:found_pg
if "%PG_BIN%"=="" (
    echo [XATOLIK] PostgreSQL o'rnatilgan papka topilmadi!
    pause
    exit /b
)

echo Ma'lumotlar bazasi tekshirilmoqda...
set PGPASSWORD=admin_password

"%PG_BIN%\psql.exe" -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'ombor_db'" | findstr "1" > NUL
if errorlevel 1 (
    echo "ombor_db" bazasi yaratilmoqda...
    "%PG_BIN%\createdb.exe" -U postgres ombor_db
    if errorlevel 1 (
        echo [XATOLIK] Baza yaratishda muammo chiqdi! Parol yoki ruxsatlarni tekshiring.
        pause
        exit /b
    )
) else (
    echo Baza allaqachon mavjud.
)

:: ---------------------------------------------------------
:: 2. PYTHON VENV YARATISH VA OFLAYN KUTUBXONALAR
:: ---------------------------------------------------------
echo.
echo [2/4] Python muhiti o'rnatilmoqda...
set "SYS_PYTHON=python"
if exist "C:\Program Files\Python311\python.exe" set "SYS_PYTHON=C:\Program Files\Python311\python.exe"

if exist env (
    echo Eski env muhiti tozalanmoqda...
    rmdir /s /q env
)
"%SYS_PYTHON%" -m venv env

echo Kutubxonalar oflayn o'rnatilmoqda... (Jarayonni kuzating)
call env\Scripts\activate
python -m pip install --upgrade pip --no-index --find-links="%BASE_DIR%\offline_packages"
pip install --no-index --find-links="%BASE_DIR%\offline_packages" -r requirements.txt
if errorlevel 1 (
    echo [XATOLIK] Kutubxonalarni o'rnatishda muammo chiqdi!
    pause
    exit /b
)

:: ---------------------------------------------------------
:: 3. DJANGO MIGRATSIYALARI
:: ---------------------------------------------------------
echo.
echo [3/4] Baza jadvallari yaratilmoqda (Migratsiya)...
python manage.py migrate --noinput
if errorlevel 1 (
    echo [XATOLIK] Migratsiya vaqtida xatolik yuz berdi. .env fayldagi parolni tekshiring!
    pause
    exit /b
)
python manage.py collectstatic --noinput

:: ---------------------------------------------------------
:: 4. NSSM XIZMATINI O'RNATISH
:: ---------------------------------------------------------
echo.
echo [4/4] Xizmat orqa fonga qo'shilmoqda...
set "NSSM_EXE=%BASE_DIR%\..\tools\nssm.exe"
set "PYTHON_EXE=%BASE_DIR%\env\Scripts\python.exe"
set "LOG_DIR=%BASE_DIR%\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Eski xizmatni o'chirish (bu yerdagi xatoliklar yashirilgan, chunki birinchi marta o'rnatganda xizmat bo'lmaydi)
"%NSSM_EXE%" stop OmborNazorat >NUL 2>&1
"%NSSM_EXE%" remove OmborNazorat confirm >NUL 2>&1

"%NSSM_EXE%" install OmborNazorat "%PYTHON_EXE%"
"%NSSM_EXE%" set OmborNazorat AppParameters "-u """%BASE_DIR%\start_server.py""""
"%NSSM_EXE%" set OmborNazorat AppDirectory "%BASE_DIR%"
"%NSSM_EXE%" set OmborNazorat AppStdout "%BASE_DIR%\logs\service_out.log"
"%NSSM_EXE%" set OmborNazorat AppStderr "%BASE_DIR%\logs\service_err.log"
"%NSSM_EXE%" set OmborNazorat Start SERVICE_AUTO_START
"%NSSM_EXE%" set OmborNazorat DisplayName "Ombor Nazorat Tizimi"

echo Service ishga tushirilmoqda...
"%NSSM_EXE%" start OmborNazorat

echo =======================================
echo ISH TUGADI! Tizim tayyor.
echo =======================================

:: Dasturni avtomatik brauzerda ochish
timeout /t 3 > NUL
start http://127.0.0.1:8000

echo Jarayon muvaffaqiyatli yakunlandi. Agar qandaydir xatoliklar (qizil yozuvlar) chiqqan bo'lsa, ularni ko'rib chiqishingiz mumkin.
:: Natijani ko'rish uchun oynani ushlab turish
pause