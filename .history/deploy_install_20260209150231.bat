@echo off
cls
echo ========================================================
echo   OMBOR NAZORAT - TIZIMNI O'RNATISH VA YANGILASH
echo ========================================================

:: 1. LOG FAYLNI BOSHLASH
:: O'rnatish jarayonini kuzatish uchun log yozamiz
set "LOGFILE=C:\ombor_install_log.txt"
echo O'rnatish boshlandi: %DATE% %TIME% > "%LOGFILE%"

:: 2. PAPKAGA O'TISH
pushd "%~dp0"
set "BASE_DIR=%~dp0"
:: Oxiridagi sleshni olib tashlash
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
echo Joriy papka: "%BASE_DIR%" >> "%LOGFILE%"

:: ---------------------------------------------------------
:: 3. ESKI JARAYONLARNI O'LDIRISH (ENG MUHIM QISM!)
:: ---------------------------------------------------------
echo Eski jarayonlar tozalanmoqda...
echo Eski jarayonlar tozalanmoqda... >> "%LOGFILE%"

:: Python va NSSM ishlab turgan bo'lsa, ularni majburan to'xtatamiz.
:: Bu "Socket" (55555 port) ni bo'shatadi.
taskkill /F /IM python.exe >> "%LOGFILE%" 2>&1
taskkill /F /IM nssm.exe >> "%LOGFILE%" 2>&1

:: Serviceni to'xtatish (agar mavjud bo'lsa)
"%BASE_DIR%\..\tools\nssm.exe" stop OmborNazorat >> "%LOGFILE%" 2>&1
"%BASE_DIR%\..\tools\nssm.exe" remove OmborNazorat confirm >> "%LOGFILE%" 2>&1

:: Tizim o'ziga kelishi uchun 3 soniya kutamiz
timeout /t 3 /nobreak >nul

:: ---------------------------------------------------------
:: 4. PYTHONNI ANIQLASH
:: ---------------------------------------------------------
set "SYS_PYTHON=python"
:: Agar aniq manzil bo'lsa, o'shani olamiz (System Pathdan ko'ra ishonchliroq)
if exist "C:\Program Files\Python311\python.exe" set "SYS_PYTHON=C:\Program Files\Python311\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

echo Python manzil: %SYS_PYTHON% >> "%LOGFILE%"

:: ---------------------------------------------------------
:: 5. VIRTUAL MUHIT (ENV)
:: ---------------------------------------------------------
:: Biz har safar envni o'chirib tashlamaymiz, vaqtni tejash uchun.
:: Faqat yo'q bo'lsa yaratamiz.
if not exist "env" (
    echo Yangi virtual muhit (env) yaratilmoqda...
    "%SYS_PYTHON%" -m venv env
) else (
    echo Virtual muhit mavjud. Davom etamiz...
)

:: Env aktivlashtirish
call env\Scripts\activate

:: ---------------------------------------------------------
:: 6. KUTUBXONALARNI O'RNATISH (OFFLINE)
:: ---------------------------------------------------------
echo Kutubxonalar tekshirilmoqda... >> "%LOGFILE%"
echo Pip yangilanmoqda...
python -m pip install --upgrade pip --no-index --find-links="offline_packages" >> "%LOGFILE%" 2>&1

echo Requirements o'rnatilmoqda...
pip install --no-index --find-links="offline_packages" -r requirements.txt >> "%LOGFILE%" 2>&1

:: ---------------------------------------------------------
:: 7. BAZA VA STATIK FAYLLAR
:: ---------------------------------------------------------
echo Baza migratsiya qilinmoqda... >> "%LOGFILE%"
python manage.py migrate --noinput >> "%LOGFILE%" 2>&1

echo Statik fayllar yig'ilmoqda... >> "%LOGFILE%"
python manage.py collectstatic --noinput >> "%LOGFILE%" 2>&1

:: ---------------------------------------------------------
:: 8. SERVICE O'RNATISH (NSSM)
:: ---------------------------------------------------------
echo Service qayta o'rnatilmoqda... >> "%LOGFILE%"

set "NSSM_EXE=%BASE_DIR%\..\tools\nssm.exe"
set "PYTHON_EXE=%BASE_DIR%\env\Scripts\python.exe"
set "LOG_DIR=%BASE_DIR%\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Serviceni o'rnatish
"%NSSM_EXE%" install OmborNazorat "%PYTHON_EXE%"
:: DIQQAT: start_server.py o'rniga to'g'ridan-to'g'ri manage.py ishlatgan ma'qul
:: --noreload juda muhim! Bo'lmasa 2 ta jarayon ochilib, socket xato beradi.
"%NSSM_EXE%" set OmborNazorat AppParameters "%BASE_DIR%\manage.py runserver 0.0.0.0:8000 --noreload"
"%NSSM_EXE%" set OmborNazorat AppDirectory "%BASE_DIR%"

:: Loglar
"%NSSM_EXE%" set OmborNazorat AppStdout "%LOG_DIR%\service_out.log"
"%NSSM_EXE%" set OmborNazorat AppStderr "%LOG_DIR%\service_err.log"

:: Avto start
"%NSSM_EXE%" set OmborNazorat Start SERVICE_AUTO_START
"%NSSM_EXE%" set OmborNazorat DisplayName "Ombor Nazorat Tizimi"
"%NSSM_EXE%" set OmborNazorat Description "Omborxona boshqaruv tizimi (Django)"

:: ---------------------------------------------------------
:: 9. ISHGA TUSHIRISH
:: ---------------------------------------------------------
echo Service start berilmoqda... >> "%LOGFILE%"
"%NSSM_EXE%" start OmborNazorat >> "%LOGFILE%" 2>&1

echo =======================================
echo O'RNATISH MUVAFFAQIYATLI TUGADI!
echo =======================================
echo Log fayl manzili: %LOGFILE%

:: Brauzerni ochish (ozgina kutib)
timeout /t 5 > NUL
start http://127.0.0.1:8000

exit