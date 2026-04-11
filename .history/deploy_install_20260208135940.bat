@echo off
:: Hozirgi papkani aniqlab olish (oxirida \ belgisi bilan)
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: ---------------------------------------------------------
:: 1. Virtual muhitni tozalash va yangidan yaratish
:: ---------------------------------------------------------
if exist env (
    echo Eski muhit tozalanmoqda...
    rmdir /s /q env
)

echo Yangi virtual muhit (env) yaratilmoqda...
python -m venv env

:: ---------------------------------------------------------
:: 2. Kutubxonalarni OFFLINE o'rnatish
:: ---------------------------------------------------------
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate
pip install --no-index --find-links="%APPDIR%offline_packages" -r requirements.txt

:: ---------------------------------------------------------
:: 3. Bazani sozlash (Migrate)
:: ---------------------------------------------------------
echo Ma'lumotlar bazasi yangilanmoqda...
python manage.py migrate --noinput
python manage.py collectstatic --noinput

:: ---------------------------------------------------------
:: 4. Windows Service (NSSM) ni mukammal sozlash
:: ---------------------------------------------------------
echo Windows Service o'rnatilmoqda...

:: Yo'llarni o'zgaruvchilarga olamiz (Tirnoqlar bilan ishlash oson bo'lishi uchun)
set NSSM_EXE="%APPDIR%..\tools\nssm.exe"
set PYTHON_EXE="%APPDIR%env\Scripts\python.exe"
set START_SCRIPT="start_server.py"
set LOG_DIR="%APPDIR%logs"

:: Log papkasini yaratamiz (xato chiqsa ko'rish uchun)
if not exist %LOG_DIR% mkdir %LOG_DIR%

:: Eski serviceni to'xtatish va o'chirish
%NSSM_EXE% stop OmborNazorat
%NSSM_EXE% remove OmborNazorat confirm

:: --- YANGI SERVICE O'RNATISH ---
:: 1. Dastur sifatida Pythonni ko'rsatamiz
%NSSM_EXE% install OmborNazorat %PYTHON_EXE%

:: 2. Argument sifatida start_server.py ni beramiz
%NSSM_EXE% set OmborNazorat AppParameters %START_SCRIPT%

:: 3. Ishchi papka (juda muhim!) - start_server.py shu yerda turibdi deb aytamiz
%NSSM_EXE% set OmborNazorat AppDirectory "%APPDIR%"

:: 4. Loglarni yoqamiz (Xato bersa logs papkasiga yozadi)
%NSSM_EXE% set OmborNazorat AppStdout "%APPDIR%logs\service_out.log"
%NSSM_EXE% set OmborNazorat AppStderr "%APPDIR%logs\service_err.log"

:: 5. Avtomatik yonadigan qilamiz
%NSSM_EXE% set OmborNazorat Start SERVICE_AUTO_START
%NSSM_EXE% set OmborNazorat DisplayName "Ombor Nazorat Tizimi"
%NSSM_EXE% set OmborNazorat Description "Omborxona uchun lokal server (Port 8000)"

:: ---------------------------------------------------------
:: 5. Ishga tushirish
:: ---------------------------------------------------------
echo Xizmat ishga tushirilmoqda...
%NSSM_EXE% start OmborNazorat

echo =======================================
echo O'RNATISH MUVAFFAQIYATLI TUGADI!
echo =======================================

:: Brauzerni ochish (ozgina kutib turib)
timeout /t 3 /nobreak > NUL
start http://127.0.0.1:8000

pause