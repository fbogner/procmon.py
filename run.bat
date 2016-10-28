@echo off
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' ( goto gotPrivileges 
)
echo You need to run this as admin
pause
exit /b 

:gotPrivileges
cd %~dp0

procmon.py -c "C:\Program Files (x86)\Dropbox\Client\Dropbox.exe"

echo ============ THE END ===============
:noend
pause
goto noend


