@echo off
cls
echo ========================================
echo   MedDigit Server Startup
echo ========================================
echo.
echo Stopping any existing servers on port 8080...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 1 /nobreak >nul
echo.
echo Starting server...
echo.
echo ========================================
echo   SERVER IS RUNNING!
echo   Open this link in your browser:
echo   http://127.0.0.1:8080
echo ========================================
echo.
python app.py
