@echo off
setlocal
pushd "%~dp0"
title Zynexra Launcher

echo ======================================
echo        Starting Zynexra
echo ======================================
echo.

REM ---- Check Ollama ----
where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama is not installed.
    echo Please install it from https://ollama.com/download
    echo After installing, run Zynexra again.
    echo.
    pause
    exit /b 1
)

REM ---- Start Ollama service (minimized window) ----
echo Starting Ollama...
start "Ollama" /min cmd /c "ollama start"
timeout /t 2 >nul

REM ---- Check Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed.
    echo Please install Python from https://python.org (check "Add to PATH").
    echo.
    pause
    exit /b 1
)

REM ---- Install/verify dependencies to user site-packages ----
echo Checking Python dependencies...
pip install --user -r requirements.txt >nul 2>nul

REM ---- Start backend ----
echo Starting Zynexra backend...
start "Zynexra Backend" cmd /k "cd /d \"%~dp0\" && uvicorn backend.app:app --host 127.0.0.1 --port 8000"

timeout /t 3 >nul

REM ---- Start frontend ----
echo Starting React frontend...
start "Zynexra UI" cmd /k "cd /d \"%~dp0\" && cd frontend-react && npm run dev"

echo.
echo Zynexra windows opened:
echo  - Backend: http://127.0.0.1:8000
echo  - Frontend: http://localhost:5173
echo Close these terminals to stop Zynexra.
echo.
pause
popd
exit /b 0
