@echo off
:: Hozirgi papkani aniqlab olish
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: ---------------------------------------------------------
:: 1. RUXSATLARNI OCHISH (ENG MUHIM QISM)
:: ---------------------------------------------------------
:: Program Files ichida bo'lsa ham, hamma foydalanuvchiga (Everyone)
:: o'qish va yozish ruxsatini beramiz. Bu CSS va Baza muammosini yechadi.
echo Papka ruxsatlari sozlanmoqda...
icacls "%APPDIR%." /grant Everyone:(OI)(CI)F /T

:: ---------------------------------------------------------
:: 2. Virtual muhitni yangilash
:: ---------------------------------------------------------
if exist env (
    echo Eski muhit tozalanmoqda...
    rmdir /s /q env
)

echo Yangi virtual muhit (env) yaratilmoqda...
python -m venv env

:: ---------------------------------------------------------
:: 3. Kutubxonalarni OFFLINE o'rnatish
:: ---------------------------------------------------------
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate
pip install --no-index --find-links="%APPDIR%offline_packages" -r requirements.txt

:: ---------------------------------------------------------
:: 4. Bazani va Statik fayllarni sozlash
:: ---------------------------------------------------------
echo Ma'lumotlar bazasi va Statik fayllar yangilanmoqda...
python manage.py migrate --noinput
python manage.py collectstatic --noinput

:: Bazaga va static papkaga qayta ruxsat beramiz (kafolat uchun)
if exist db.sqlite3 icacls "db.sqlite3" /grant Everyone:F
if exist staticfiles icacls "staticfiles" /grant Everyone:(OI)(CI)F /T

:: ---------------------------------------------------------
:: 5. Windows Service (NSSM) sozlash
:: ---------------------------------------------------------
echo Windows Service o'rnatilmoqda...

set NSSM_EXE="%APPDIR%..\tools\nssm.exe"
set PYTHON_EXE="%APPDIR%env\Scripts\python.exe"
set START_SCRIPT="start_server.py"
set LOG_DIR="%APPDIR%logs"

if not exist %LOG_DIR% mkdir %LOG_DIR%
icacls %LOG_DIR% /grant Everyone:(OI)(CI)F /T

:: Eski serviceni to'xtatish va o'chirish
%NSSM_EXE% stop OmborNazorat
%NSSM_EXE% remove OmborNazorat confirm

:: --- YANGI SERVICE O'RNATISH ---
%NSSM_EXE% install OmborNazorat %PYTHON_EXE%

:: Argumentlar
%NSSM_EXE% set OmborNazorat AppParameters %START_SCRIPT%
%NSSM_EXE% set OmborNazorat AppDirectory "%APPDIR%"
%NSSM_EXE% set OmborNazorat AppStdout "%APPDIR%logs\service_out.log"
%NSSM_EXE% set OmborNazorat AppStderr "%APPDIR%logs\service_err.log"

:: Avtomatik yonish va tavsif
%NSSM_EXE% set OmborNazorat Start SERVICE_AUTO_START
%NSSM_EXE% set OmborNazorat DisplayName "Ombor Nazorat Tizimi"
%NSSM_EXE% set OmborNazorat Description "Omborxona tizimi (Port 8000)"

:: ---------------------------------------------------------
:: 6. Ishga tushirish
:: ---------------------------------------------------------
echo Xizmat ishga tushirilmoqda...
%NSSM_EXE% start OmborNazorat

echo =======================================
echo O'RNATISH MUVAFFAQIYATLI TUGADI!
echo =======================================

:: Brauzerni ochish
timeout /t 5 /nobreak > NUL
start http://127.0.0.1:8000

pause