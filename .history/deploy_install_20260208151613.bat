@echo off
:: Eng boshida to'xtab turadi (Oyna ochilganini ko'rish uchun)
echo Skript ishga tushdi...
timeout /t 2 > NUL

:: Hozirgi papkani aniqlab olish
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: ---------------------------------------------------------
:: 0. PYTHONNI QIDIRISH
:: ---------------------------------------------------------
set "SYS_PYTHON=python"

:: DIQQAT: Qavs ichida izoh yozish mumkin emas, shuning uchun toza kod:
if exist "C:\Program Files\Python311\python.exe" (
    set "SYS_PYTHON=C:\Program Files\Python311\python.exe"
    echo Python (Global 64-bit) topildi.
) else (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        echo Python (User 64-bit) topildi.
    ) else (
        echo DIQQAT: Aniq Python topilmadi, tizim standarti ishlatiladi.
    )
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
"%SYS_PYTHON%" -m venv env

:: ---------------------------------------------------------
:: 3. Kutubxonalarni OFFLINE o'rnatish
:: ---------------------------------------------------------
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate

python -m pip install --upgrade pip --no-index --find-links="%APPDIR%offline_packages" >NUL 2>&1
pip install --no-index --find-links="%APPDIR%offline_packages" -r requirements.txt

:: ---------------------------------------------------------
:: 4. Bazani va Statik fayllarni sozlash
:: ---------------------------------------------------------
echo Ma'lumotlar bazasi va Statik fayllar yangilanmoqda...
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if exist db.sqlite3 icacls "db.sqlite3" /grant *S-1-1-0:F >NUL
if exist staticfiles icacls "staticfiles" /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: ---------------------------------------------------------
:: 5. Windows Service (NSSM) SOZLASH
:: ---------------------------------------------------------
echo Windows Service o'rnatilmoqda...

set "BASE_DIR=%APPDIR:~0,-1%"
set NSSM_EXE="%BASE_DIR%\..\tools\nssm.exe"
set PYTHON_EXE="%BASE_DIR%\env\Scripts\python.exe"
set LOG_DIR="%BASE_DIR%\logs"

if not exist %LOG_DIR% mkdir %LOG_DIR%
icacls %LOG_DIR% /grant *S-1-1-0:(OI)(CI)F /T >NUL

%NSSM_EXE% stop OmborNazorat >NUL 2>&1
%NSSM_EXE% remove OmborNazorat confirm >NUL 2>&1

:: Service o'rnatish
%NSSM_EXE% install OmborNazorat %PYTHON_EXE%
%NSSM_EXE% set OmborNazorat AppParameters "-u \"%BASE_DIR%\start_server.py\""
%NSSM_EXE% set OmborNazorat AppDirectory "%BASE_DIR%"
%NSSM_EXE% set OmborNazorat AppStdout "%BASE_DIR%\logs\service_out.log"
%NSSM_EXE% set OmborNazorat AppStderr "%BASE_DIR%\logs\service_err.log"
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