@echo off
:: Ekranni tozalaymiz
cls

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: 1. Papkaga o'tish (Xavfsiz usul)
pushd "%~dp0"
set "BASE_DIR=%~dp0"
:: Oxiridagi teskari sleshni (\) olib tashlaymiz (NSSM uchun kerak)
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

echo Joriy papka: "%BASE_DIR%"

:: ---------------------------------------------------------
:: 2. PYTHONNI QIDIRISH (Qavssiz, oddiy usul)
:: ---------------------------------------------------------
set "SYS_PYTHON=python"

:: Agar C diskda bo'lsa
if exist "C:\Program Files\Python311\python.exe" set "SYS_PYTHON=C:\Program Files\Python311\python.exe"

:: Agar User papkasida bo'lsa
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

echo Python manzil: %SYS_PYTHON%

:: ---------------------------------------------------------
:: 3. RUXSATLARNI OCHISH
:: ---------------------------------------------------------
echo Ruxsatlar berilmoqda...
icacls "%BASE_DIR%" /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: ---------------------------------------------------------
:: 4. VIRTUAL MUHIT (ENV)
:: ---------------------------------------------------------
if exist env (
    echo Eski env tozalanmoqda...
    rmdir /s /q env
)

echo Yangi env yaratilmoqda...
"%SYS_PYTHON%" -m venv env

:: Agar env yaratish o'xshamasa, to'xtasin
if not exist env\Scripts\activate (
    echo XATOLIK: Virtual muhit yaratilmadi!
    pause
    exit
)

:: ---------------------------------------------------------
:: 5. KUTUBXONALARNI O'RNATISH
:: ---------------------------------------------------------
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate

python -m pip install --upgrade pip --no-index --find-links="offline_packages" >NUL 2>&1
pip install --no-index --find-links="offline_packages" -r requirements.txt

:: ---------------------------------------------------------
:: 6. BAZA VA STATIK FAYLLAR
:: ---------------------------------------------------------
echo Baza sozlanmoqda...
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if exist db.sqlite3 icacls "db.sqlite3" /grant *S-1-1-0:F >NUL
if exist staticfiles icacls "staticfiles" /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: ---------------------------------------------------------
:: 7. SERVICE O'RNATISH (Ehtiyotkorona)
:: ---------------------------------------------------------
echo Service o'rnatilmoqda...

set "NSSM_EXE=%BASE_DIR%\..\tools\nssm.exe"
set "PYTHON_EXE=%BASE_DIR%\env\Scripts\python.exe"
set "LOG_DIR=%BASE_DIR%\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
icacls "%LOG_DIR%" /grant *S-1-1-0:(OI)(CI)F /T >NUL

:: Serviceni tozalash
"%NSSM_EXE%" stop OmborNazorat >NUL 2>&1
"%NSSM_EXE%" remove OmborNazorat confirm >NUL 2>&1

:: O'rnatish
"%NSSM_EXE%" install OmborNazorat "%PYTHON_EXE%"
:: Argumentlar (Probel va tirnoqlar muammosini hal qilish)
"%NSSM_EXE%" set OmborNazorat AppParameters "-u """%BASE_DIR%\start_server.py""""
"%NSSM_EXE%" set OmborNazorat AppDirectory "%BASE_DIR%"

:: Loglar
"%NSSM_EXE%" set OmborNazorat AppStdout "%BASE_DIR%\logs\service_out.log"
"%NSSM_EXE%" set OmborNazorat AppStderr "%BASE_DIR%\logs\service_err.log"

:: Start
"%NSSM_EXE%" set OmborNazorat Start SERVICE_AUTO_START
"%NSSM_EXE%" set OmborNazorat DisplayName "Ombor Nazorat Tizimi"
"%NSSM_EXE%" set OmborNazorat Description "Omborxona tizimi (Port 8000)"

echo Service ishga tushirilmoqda...
"%NSSM_EXE%" start OmborNazorat

echo =======================================
echo ISH TUGADI! 
echo =======================================
echo Iltimos, pastdagi yozuvlarga qarang. Xatolik bormi?
echo Agar xato bo'lsa, uni rasmga oling.

timeout /t 5 > NUL
start http://127.0.0.1:8000

:: MUAOMMO BO'LSA OYNA YOPILMASLIGI UCHUN:
pause