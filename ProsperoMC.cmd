@echo off
setlocal
set "action=%~1"
set "hostAddress=%~2"
set "port=%~3"
set "interactive="
if not defined hostAddress set "hostAddress=192.168.1.111"
if not defined port set "port=2121"
if defined action goto run
set "interactive=1"
echo ProsperoMC - build and update your PS5
echo.
echo 1. Build Java launcher and native app
echo 2. Send the current app build to PS5
echo 3. Build and send to PS5
echo 4. Exit
choice /c 1234 /n /m "Choose 1-4: "
if errorlevel 4 exit /b 0
if errorlevel 3 (set "action=build-send") else if errorlevel 2 (set "action=send") else (set "action=build")
:run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build-send-ps5.ps1" -Action "%action%" -HostAddress "%hostAddress%" -Port "%port%"
set "result=%errorlevel%"
if defined interactive pause
exit /b %result%
