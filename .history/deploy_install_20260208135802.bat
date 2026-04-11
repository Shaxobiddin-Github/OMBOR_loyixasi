:: 4. Windows Service (NSSM) ni sozlash
echo Windows Service o'rnatilmoqda...
set NSSM="%APPDIR%..\tools\nssm.exe"
set PYTHON_EXE="%APPDIR%env\Scripts\python.exe"
set START_SCRIPT="%APPDIR%start_server.py"

:: Eskisini tozalash
%NSSM% stop OmborNazorat
%NSSM% remove OmborNazorat confirm

:: Yangi service o'rnatish (Tirnoqlar bilan ehtiyotkorona)
%NSSM% install OmborNazorat %PYTHON_EXE% %START_SCRIPT%

:: MUHIM: Xizmatga qaysi papkada ishlashni uqtirish
%NSSM% set OmborNazorat AppDirectory "%APPDIR%"

:: MUHIM: Xizmat avtomatik yonsin
%NSSM% set OmborNazorat Start SERVICE_AUTO_START

:: Xatolar bo'lsa log yozish (muammoni ko'rish uchun)
%NSSM% set OmborNazorat AppStdout "%APPDIR%logs\service_out.log"
%NSSM% set OmborNazorat AppStderr "%APPDIR%logs\service_err.log"

:: Papka yaratish (log uchun)
if not exist "%APPDIR%logs" mkdir "%APPDIR%logs"

:: Xizmatni yurgizish
%NSSM% start OmborNazorat