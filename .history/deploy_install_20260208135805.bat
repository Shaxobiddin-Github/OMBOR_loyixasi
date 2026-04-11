@echo off
set APPDIR=%~dp0
cd /d "%APPDIR%"

echo =======================================
echo TIZIMNI SOZLASH BOSHLANDI...
echo =======================================

:: 1. Virtual muhitni tozalash va yangidan yaratish
:: Bu boshqa kompyuterda Python yo'llari xato bo'lmasligini ta'minlaydi
if exist env (
    echo Eski muhit o'chirilmoqda...
    rmdir /s /q env
)
echo Yangi virtual muhit yaratilmoqda...
python -m venv env

:: 2. Muhitni faollashtirish va paketlarni OFFLINE o'rnatish
echo Kutubxonalar o'rnatilmoqda...
call env\Scripts\activate
pip install --no-index --find-links="%APPDIR%offline_packages" -r requirements.txt

:: 3. Ma'lumotlar bazasini tayyorlash
echo Ma'lumotlar bazasi sozlanmoqda...
python manage.py migrate --noinput

:: 4. Windows Service (NSSM) ni sozlash
echo Windows Service o'rnatilmoqda...
set NSSM="%APPDIR%..\tools\nssm.exe"

:: Eskisini o'chirib, yangisini o'rnatish
%NSSM% stop OmborNazorat
%NSSM% remove OmborNazorat confirm
%NSSM% install OmborNazorat "%APPDIR%env\Scripts\python.exe" "%APPDIR%start_server.py"
%NSSM% set OmborNazorat AppDirectory "%APPDIR%"
%NSSM% set OmborNazorat Start SERVICE_AUTO_START

:: Xizmatni yurgizish
%NSSM% start OmborNazorat

echo =======================================
echo O'RNATISH TUGADI!
echo =======================================
pause