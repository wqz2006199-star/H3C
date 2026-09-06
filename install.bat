@echo off
chcp 65001 >nul
title Install H3C Config Parser
echo ==========================================
echo   Installing dependencies...
echo ==========================================
echo.
cd /d %~dp0backend
python -m pip install -r requirements.txt
echo.
echo ==========================================
echo   Installation complete!
echo ==========================================
echo.
echo Now double-click start.bat to launch the app.
echo.
pause