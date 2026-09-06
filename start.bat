@echo off
chcp 65001 >nul
title H3C Config Parser V3.0
echo ==========================================
echo   H3C Config Parser V3.0
echo ==========================================
echo.
echo [1/3] Starting backend (port 8000)...
start "Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak
echo [OK] Backend started
echo.
echo [2/3] Starting frontend (port 5500)...
start "Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 5500"
timeout /t 2 /nobreak
echo [OK] Frontend started
echo.
echo ==========================================
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://127.0.0.1:5500
echo ==========================================
echo.
echo Opening browser...
start http://127.0.0.1:5500
echo.
echo Keep both windows open while using the app.
pause >nul