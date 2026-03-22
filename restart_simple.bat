@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo 正在关闭 Flask...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5001"') do (
    echo 关闭进程: %%a
    taskkill /PID %%a /F 2>nul
)

echo.
echo 等待2秒...
timeout /t 2 /nobreak >nul

echo.
echo 启动新的 Flask 实例...
start "Flask Backend" cmd /k ".env\Scripts\python.exe backend/app.py"

echo.
echo 等待3秒以确保启动完成...
timeout /t 3 /nobreak >nul

echo.
echo 访问地址: http://localhost:5001
echo.
