@echo off
:: Hozirgi papkani aniqlab olish
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: 1. RUXSATLARNI OCHISH (Universal *S-1-1-0)
echo Papka ruxsatlari sozlanmoqda...
icacls "%APPDIR%." /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: 2. Virtual muhitni yangilash
if exist env (
    echo Eski muhit tozalanmoqda...
    rmdir /s /q env
)

echo Yangi virtual muhit (env) yaratilmoqda...
python -m venv env

:: 3. Kutubxonalarni OFFLINE o'rnatish
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate
pip install --no-index --find-links="%APPDIR%offline_packages" -r requirements.txt

:: 4. Bazani va Statik fayllarni sozlash
echo Ma'lumotlar bazasi va Statik fayllar yangilanmoqda...
python manage.py migrate --noinput
python manage.py collectstatic --noinput

:: Ruxsatlar (qayta)
if exist db.sqlite3 icacls "db.sqlite3" /grant *S-1-1-0:F >NUL
if exist staticfiles icacls "staticfiles" /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: ---------------------------------------------------------
:: 5. Windows Service (NSSM) - DEBUG REJIMIDA
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
%NSSM_EXE% stop OmborNazorat
%NSSM_EXE% remove OmborNazorat confirm

:: --- YANGI SERVICE O'RNATISH ---
:: Dastur: Python.exe
%NSSM_EXE% install OmborNazorat %PYTHON_EXE%

:: Argumentlar: -u (buferlamaslik) va start_server.py ning TO'LIQ manzili
:: DIQQAT: Tirnoqlarga e'tibor bering!
%NSSM_EXE% set OmborNazorat AppParameters "-u \"%BASE_DIR%\start_server.py\""

:: Ishchi papka
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

:: Agar xato bo'lsa, logni darhol ochib ko'rsatish (Tekshirish uchun)
timeout /t 2 /nobreak > NUL
type "%BASE_DIR%\logs\service_err.log"

:: Brauzerni ochish
timeout /t 5 /nobreak > NUL
start http://127.0.0.1:8000

pause