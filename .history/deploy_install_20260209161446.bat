@echo off
:: Hozirgi papkani aniqlab olish
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: ---------------------------------------------------------
:: 0. PYTHONNI QIDIRISH (ENG MUHIM QISM)
:: ---------------------------------------------------------
:: Bizga aniq 64-bit Python kerak. Tizimdagi eski 32-bitli python 
:: bizning ishimizni buzmasligi uchun, Python 3.11 ni aniq manzildan qidiramiz.

set SYS_PYTHON=python
:: Agar C diskda Python 3.11 bor bo'lsa, o'shani ishlatamiz (bu 64-bit bo'ladi)
if exist "C:\Program Files\Python311\python.exe" (
    set SYS_PYTHON="C:\Program Files\Python311\python.exe"
    echo Python 3.11 (64-bit) topildi: "C:\Program Files\Python311\python.exe"
) else (
    echo DIQQAT: Aniq Python topilmadi, tizimdagi standart python ishlatiladi.
)

:: ---------------------------------------------------------
:: 1. RUXSATLARNI OCHISH
:: ---------------------------------------------------------
echo Papka ruxsatlari sozlanmoqda...
icacls "%APPDIR%." /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: ---------------------------------------------------------
:: 2. Virtual muhitni yangilash
:: ---------------------------------------------------------
if exist env (
    echo Eski muhit tozalanmoqda...
    rmdir /s /q env
)

echo Yangi virtual muhit (env) yaratilmoqda...
:: MANA SHU YERDA SYS_PYTHON ISHLATILADI
%SYS_PYTHON% -m venv env

:: ---------------------------------------------------------
:: 3. Kutubxonalarni OFFLINE o'rnatish
:: ---------------------------------------------------------
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate

:: Pipni yangilab olamiz (xavfsizlik uchun)
python -m pip install --upgrade pip --no-index --find-links="%APPDIR%offline_packages" >NUL 2>&1

:: Asosiy kutubxonalar
pip install --no-index --find-links="%APPDIR%offline_packages" -r requirements.txt

:: ---------------------------------------------------------
:: 4. Bazani va Statik fayllarni sozlash
:: ---------------------------------------------------------
echo Ma'lumotlar bazasi va Statik fayllar yangilanmoqda...
python manage.py migrate --noinput
python manage.py collectstatic --noinput

:: Ruxsatlar
if exist db.sqlite3 icacls "db.sqlite3" /grant *S-1-1-0:F >NUL
if exist staticfiles icacls "staticfiles" /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: ---------------------------------------------------------
:: 5. Windows Service (NSSM) SOZLASH
:: ---------------------------------------------------------
echo Windows Service o'rnatilmoqda...

:: Yo'llarni aniq qilib olamiz (Oxiridagi \ belgisini olib tashlaymiz)
set "BASE_DIR=%APPDIR:~0,-1%"

set NSSM_EXE="%BASE_DIR%\..\tools\nssm.exe"
set PYTHON_EXE="%BASE_DIR%\env\Scripts\python.exe"
set LOG_DIR="%BASE_DIR%\logs"

:: Log papkasi
if not exist %LOG_DIR% mkdir %LOG_DIR%
icacls %LOG_DIR% /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: Eski serviceni tozalash
%NSSM_EXE% stop OmborNazorat >NUL 2>&1
%NSSM_EXE% remove OmborNazorat confirm >NUL 2>&1

:: --- YANGI SERVICE O'RNATISH ---
%NSSM_EXE% install OmborNazorat %PYTHON_EXE%

:: Argumentlar (Debug rejimi -u va to'liq yo'l)
%NSSM_EXE% set OmborNazorat AppParameters "-u \"%BASE_DIR%\start_server.py\""
%NSSM_EXE% set OmborNazorat AppDirectory "%BASE_DIR%"

:: Loglar
%NSSM_EXE% set OmborNazorat AppStdout "%BASE_DIR%\logs\service_out.log"
%NSSM_EXE% set OmborNazorat AppStderr "%BASE_DIR%\logs\service_err.log"

:: Avtomatik yonish
%NSSM_EXE% set OmborNazorat Start SERVICE_AUTO_START
%NSSM_EXE% set OmborNazorat DisplayName "Ombor Nazorat Tizimi"
%NSSM_EXE% set OmborNazorat Description "Omborxona tizimi (Port 8000)"

:: ---------------------------------------------------------
:: 6. Ishga tushirish
:: ---------------------------------------------------------
echo Xizmat ishga tushirilmoqda...
%NSSM_EXE% start OmborNazorat

echo =======================================
echo O'RNATISH TUGADI!
echo =======================================

timeout /t 5 /nobreak > NUL
start http://127.0.0.1:8000

pause