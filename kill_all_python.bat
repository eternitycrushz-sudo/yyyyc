@echo off
chcp 65001 >nul
echo ========================================
echo  清理所有 Python 进程和端口
echo ========================================
echo.

echo [1] 查找所有 Python 进程...
tasklist | findstr python.exe
echo.

echo [2] 强制终止所有 Python 进程...
taskkill /F /IM python.exe /T 2>nul
if %errorlevel% equ 0 (
    echo     ✓ Python 进程已清理
) else (
    echo     ℹ 没有运行中的 Python 进程
)
echo.

echo [3] 查找占用 5000 端口的进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo     发现进程 PID: %%a
    taskkill /F /PID %%a 2>nul
    if !errorlevel! equ 0 (
        echo     ✓ 已终止进程 %%a
    )
)
echo.

echo [4] 查找占用 5672 端口的进程（RabbitMQ）...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5672 ^| findstr LISTENING') do (
    echo     发现进程 PID: %%a
    taskkill /F /PID %%a 2>nul
    if !errorlevel! equ 0 (
        echo     ✓ 已终止进程 %%a
    )
)
echo.

echo [5] 查找占用 15672 端口的进程（RabbitMQ 管理界面）...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :15672 ^| findstr LISTENING') do (
    echo     发现进程 PID: %%a
    taskkill /F /PID %%a 2>nul
    if !errorlevel! equ 0 (
        echo     ✓ 已终止进程 %%a
    )
)
echo.

echo [6] 清理完成！当前端口状态：
echo.
echo 端口 5000:
netstat -ano | findstr :5000 | findstr LISTENING
if %errorlevel% neq 0 echo     ✓ 端口 5000 已释放
echo.
echo 端口 5672:
netstat -ano | findstr :5672 | findstr LISTENING
if %errorlevel% neq 0 echo     ✓ 端口 5672 已释放
echo.
echo 端口 15672:
netstat -ano | findstr :15672 | findstr LISTENING
if %errorlevel% neq 0 echo     ✓ 端口 15672 已释放
echo.

echo ========================================
echo  清理完成！
echo ========================================
pause
