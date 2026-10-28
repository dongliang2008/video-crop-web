@echo off
title Video Crop Web (8010)
cd /d %~dp0
echo ============================================
echo   Video Crop Web  (video-crop-web)
echo   URL: http://127.0.0.1:8010
echo ============================================
echo [1/3] Checking port 8010 ...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8010 " ^| findstr "LISTENING"') do (
  set FOUND=1
  echo      Port 8010 in use by PID %%a, killing it...
  taskkill /F /PID %%a >nul 2>&1
)
if "%FOUND%"=="1" (
  timeout /t 1 /nobreak >nul
  echo      Occupied process cleaned.
) else (
  echo      Port 8010 is free.
)
echo [2/3] Starting service...
start "" http://127.0.0.1:8010
echo [3/3] Service running. Close this window to exit.
python -m server.app
pause
