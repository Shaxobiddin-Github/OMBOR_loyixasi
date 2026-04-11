@echo off
:: Hozirgi papkani aniqlab olish
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: ---------------------------------------------------------
:: 1. RUXSATLARNI OCHISH (UNIVERSAL USUL - *S-1-1-0)
:: ---------------------------------------------------------
:: Bu kod "Everyone" yoki "Все" guruhiga papkaga to'liq ruxsat beradi.
echo Papka ruxsatlari sozlanmoqda...
icacls "%APPDIR%." /grant *S-1-1-0:(OI)(CI)F /T

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
if exist db.sqlite3 icacls "db.sqlite3" /grant *S-1-1-0:F
if exist staticfiles icacls "staticfiles" /grant *S-1-1-0:(OI)(CI)F /T

:: ---------------------------------------------------------
:: 5. Windows Service (NSSM) sozlash
:: ---------------------------------------------------------
echo Windows Service o'rnatilmoqda...

:: O'zgaruvchilarni tirnoq bilan belgilaymiz (Probel uchun muhim)
set NSSM_EXE="%APPDIR%..\tools\nssm.exe"
set PYTHON_EXE="%APPDIR%env\Scripts\python.exe"
set LOG_DIR="%APPDIR%logs"

:: Log papkasini yaratamiz va ruxsat beramiz
if not exist %LOG_DIR% mkdir %LOG_DIR%
icacls %LOG_DIR% /grant *S-1-1-0:(OI)(CI)F /T

:: Eski serviceni to'xtatish va o'chirish
%NSSM_EXE% stop OmborNazorat
%NSSM_EXE% remove OmborNazorat confirm

:: --- YANGI SERVICE O'RNATISH ---
:: 1. Dastur sifatida Pythonni ko'rsatamiz
%NSSM_EXE% install OmborNazorat %PYTHON_EXE%

:: 2. Argument sifatida start_server.py ni beramiz (Tirnoq ichida!)
%NSSM_EXE% set OmborNazorat AppParameters "start_server.py"

:: 3. Ishchi papka (Juda muhim - start_server.py shu yerda turibdi)
%NSSM_EXE% set OmborNazorat AppDirectory "%APPDIR%"

:: 4. Loglarni yoqamiz
%NSSM_EXE% set OmborNazorat AppStdout "%APPDIR%logs\service_out.log"
%NSSM_EXE% set OmborNazorat AppStderr "%APPDIR%logs\service_err.log"

:: 5. Avtomatik yonadigan va tavsifli qilamiz
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

:: Brauzerni ochish (10 soniya kutib, server o'nglanib olsin)
timeout /t 10 /nobreak > NUL
start http://127.0.0.1:8000

pause