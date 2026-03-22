@echo off
chcp 65001 >nul
echo.
echo ========================================
echo RabbitMQ 队列清理工具
echo ========================================
echo.

REM 检查虚拟环境
if not exist ".env\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境
    pause
    exit /b 1
)

REM 运行清理脚本
.env\Scripts\python.exe clean_queues.py --force

echo.
pause
