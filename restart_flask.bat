@echo off
chcp 65001 >nul
title Restart Flask Backend

echo.
echo ==========================================
echo    重启 Flask 后端
echo ==========================================
echo.

REM 杀死现有的 Flask 进程
echo [1/3] 关闭现有 Flask 进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr 5001') do (
    taskkill /PID %%a /F 2>nul
)

REM 等待端口释放
echo [2/3] 等待端口释放...
timeout /t 2 /nobreak >nul

REM 重启 Flask
echo [3/3] 启动新的 Flask 实例...
cd /d "%~dp0"
start "Flask Backend - 5001" cmd /k "title Flask Backend - 5001 && color 0A && .env\Scripts\python.exe backend/app.py"

echo.
echo ==========================================
echo    Flask 已重启！
echo ==========================================
echo.
echo 访问地址: http://localhost:5001
echo.
pause
