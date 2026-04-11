@echo off
cls
echo ========================================================
echo   OMBOR NAZORAT - TIZIMNI O'RNATISH VA YANGILASH
echo ========================================================

:: 1. LOG FAYLNI TAYYORLASH
set "LOGFILE=C:\ombor_install_log.txt"
echo O'rnatish boshlandi: %DATE% %TIME% > "%LOGFILE%"

:: 2. PAPKAGA O'TISH
cd /d "%~dp0"
set "BASE_DIR=%cd%"
echo Joriy papka: "%BASE_DIR%" >> "%LOGFILE%"

:: 3. ESKI JARAYONLARNI TOZALASH
echo Eski jarayonlar tozalanmoqda...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM nssm.exe /T >nul 2>&1

:: NSSM manzilini aniqlash
set "NSSM_EXE=%BASE_DIR%\..\tools\nssm.exe"

if exist "%NSSM_EXE%" (
    "%NSSM_EXE%" stop OmborNazorat >nul 2>&1
    "%NSSM_EXE%" remove OmborNazorat confirm >nul 2>&1
)

timeout /t 2 /nobreak >nul

:: 4. PYTHONNI TEKSHIRISH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo XATOLIK: Tizimda Python topilmadi! >> "%LOGFILE%"
    echo XATOLIK: Tizimda Python topilmadi! Iltimos, Python o'rnatilganini tekshiring.
    pause
    exit /b
)
set "SYS_PYTHON=python"

:: 5. VIRTUAL MUHIT (ENV)
if not exist "env" (
    echo Yangi virtual muhit yaratilmoqda...
    "%SYS_PYTHON%" -m venv env
)
set "ENV_PYTHON=%BASE_DIR%\env\Scripts\python.exe"

:: 6. KUTUBXONALAR (OFFLINE)
echo Kutubxonalar o'rnatilmoqda...
"%ENV_PYTHON%" -m pip install --upgrade pip --no-index --find-links="offline_packages" >> "%LOGFILE%" 2>&1
"%ENV_PYTHON%" -m pip install --no-index --find-links="offline_packages" -r requirements.txt >> "%LOGFILE%" 2>&1

:: 7. BAZA VA STATIK FAYLLAR
echo Baza va statik fayllar sozlanmoqda...
"%ENV_PYTHON%" manage.py migrate --noinput >> "%LOGFILE%" 2>&1
"%ENV_PYTHON%" manage.py collectstatic --noinput >> "%LOGFILE%" 2>&1

:: 8. SERVICE O'RNATISH (NSSM orqali)
if exist "%NSSM_EXE%" (
    echo Service o'rnatilmoqda...
    :: --noreload bayrog'i socket xatosi (55555 port) chiqmasligi uchun shart!
    "%NSSM_EXE%" install OmborNazorat "%ENV_PYTHON%" "%BASE_DIR%\manage.py runserver 0.0.0.0:8000 --noreload" >> "%LOGFILE%" 2>&1
    "%NSSM_EXE%" set OmborNazorat AppDirectory "%BASE_DIR%" >> "%LOGFILE%" 2>&1
    "%NSSM_EXE%" start OmborNazorat >> "%LOGFILE%" 2>&1
) else (
    echo XATOLIK: nssm.exe topilmadi! Manzil: %NSSM_EXE% >> "%LOGFILE%"
)

echo =======================================
echo ISH TUGADI! Log faylni tekshiring: %LOGFILE%
echo =======================================

:: Avtomatik brauzerni ochish
timeout /t 3 >nul
start http://127.0.0.1:8000

pause