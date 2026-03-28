@echo off
chcp 65001 >nul 2>nul
setlocal enabledelayedexpansion
title DY Analysis System - Launcher
color 0B

echo.
echo  ==========================================
echo     DY E-commerce Analysis System
echo     Start Script (RabbitMQ + Flask + Workers)
echo  ==========================================
echo.

:: Switch to script directory
cd /d "%~dp0"

:: ============================================
:: [0] Clean up old processes
:: ============================================
echo [0/5] Cleaning up old processes...
for /f "tokens=2 delims=," %%a in ('tasklist /fi "WINDOWTITLE eq Flask*" /fo csv /nh 2^>nul ^| findstr /i "python"') do (
    taskkill /f /pid %%~a >nul 2>&1
)
for /f "tokens=2 delims=," %%a in ('tasklist /fi "WINDOWTITLE eq Workers*" /fo csv /nh 2^>nul ^| findstr /i "python"') do (
    taskkill /f /pid %%~a >nul 2>&1
)
echo       Done

:: ============================================
:: [1] Check virtual environment
:: ============================================
echo [1/5] Checking Python venv...
if not exist ".env\Scripts\python.exe" (
    echo.
    echo  [ERROR] Virtual env .env not found
    echo  Please run setup_env.bat first
    echo.
    pause
    exit /b 1
)
echo       OK

:: ============================================
:: [2] Check MySQL connection
:: ============================================
echo [2/5] Checking MySQL...
.env\Scripts\python.exe -c "import pymysql; conn=pymysql.connect(host='localhost',port=3306,user='root',password='123456',database='dy_analysis_system',connect_timeout=3); conn.close(); print('      OK')"
if errorlevel 1 (
    echo       [WARN] MySQL connection failed
    echo         - Make sure MySQL is running
    echo         - Check password in config.py
    echo.
    set /p "CONTINUE=Continue anyway? (y/n): "
    if /i not "!CONTINUE!"=="y" exit /b 1
)

:: ============================================
:: [3] Check and start RabbitMQ
:: ============================================
echo [3/5] Checking RabbitMQ...
sc query RabbitMQ >nul 2>&1
if errorlevel 1 (
    echo       [WARN] RabbitMQ service not installed
    goto skip_rabbitmq
)

sc query RabbitMQ | findstr "RUNNING" >nul 2>&1
if errorlevel 1 (
    echo       RabbitMQ not running, starting...
    net start RabbitMQ >nul 2>&1
    if errorlevel 1 (
        echo       [WARN] Failed to start RabbitMQ, try running as admin
    ) else (
        timeout /t 3 /nobreak >nul
        echo       OK - RabbitMQ started
    )
) else (
    echo       OK - RabbitMQ running
)

.env\Scripts\python.exe -c "import pika; conn=pika.BlockingConnection(pika.ConnectionParameters('localhost',5672,credentials=pika.PlainCredentials('guest','guest'),connection_attempts=2,retry_delay=1,socket_timeout=5)); conn.close(); print('      OK - Connection verified')"
if errorlevel 1 (
    echo       [WARN] RabbitMQ connection failed
    echo         - Admin panel: http://localhost:15672
)

:skip_rabbitmq

:: ============================================
:: [4] Start Flask backend
:: ============================================
echo [4/5] Starting Flask (port 5001)...
start "Flask - Port 5001" cmd /k "cd /d %~dp0 && title Flask - Port 5001 && color 0A && .env\Scripts\python.exe backend\app.py"
timeout /t 3 /nobreak >nul
echo       OK

:: ============================================
:: [5] Start crawler Workers
:: ============================================
echo [5/5] Starting Workers...
start "Workers - Crawler" cmd /k "cd /d %~dp0 && title Workers - Crawler && color 0E && .env\Scripts\python.exe -m crawler.workers.run_workers"
timeout /t 2 /nobreak >nul
echo       OK

:: Open browser
echo.
echo       Opening browser...
start http://localhost:5001

:: ============================================
:: Done
:: ============================================
echo.
echo  ==========================================
echo    All services started!
echo  ------------------------------------------
echo.
echo    Web UI:    http://localhost:5001
echo    RabbitMQ:  http://localhost:15672
echo.
echo    Account:   admin / admin123
echo.
echo    Tip: Closing this window won't stop services
echo    To stop, close Flask and Workers windows
echo  ==========================================
echo.
pause
