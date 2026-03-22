@echo off
chcp 65001 >nul
echo ========================================
echo  完全重置系统（停止Worker + 清理队列）
echo ========================================
echo.

REM 检查虚拟环境
if not exist ".env\Scripts\python.exe" (
    echo 错误: 未找到虚拟环境
    echo 请先运行 setup_env.bat 创建虚拟环境
    pause
    exit /b 1
)

echo [步骤 1/2] 停止所有 Worker 进程...
echo.

REM 关闭 Crawler Workers 窗口
taskkill /FI "WINDOWTITLE eq Crawler Workers*" /F 2>nul

REM 等待进程完全停止
timeout /t 2 /nobreak >nul

echo   ✓ Worker 进程已停止
echo.

echo [步骤 2/2] 清理消息队列...
echo.

REM 运行清理脚本（使用虚拟环境的 Python）
cd /d %~dp0
.env\Scripts\python.exe clean_queues.py --force

echo.
echo ========================================
echo  重置完成！
echo ========================================
echo.
echo 现在可以安全地重新启动系统了。
echo.

pause
