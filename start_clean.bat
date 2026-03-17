@echo off
chcp 65001 >nul
echo ========================================
echo  抖音电商热点数据可视化分析系统
echo  (清理模式 - 会清空所有队列消息)
echo ========================================
echo.

echo [1] 检查 RabbitMQ...
docker ps | findstr rabbitmq >nul
if %errorlevel% neq 0 (
    echo     启动 RabbitMQ...
    docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
    timeout /t 10 >nul
) else (
    echo     RabbitMQ 已运行
)

echo.
echo [2] 清理所有队列消息...
.env\Scripts\python.exe clean_queues.py --force
if %errorlevel% neq 0 (
    echo     警告: 清理队列失败
    pause
    exit /b 1
)

echo.
echo [3] 启动 Flask 后端...
start "Flask Backend" cmd /k "cd /d %~dp0 && .env\Scripts\python.exe backend/app.py"

echo.
echo [4] 启动爬虫 Workers...
start "Crawler Workers" cmd /k "cd /d %~dp0 && .env\Scripts\python.exe -m crawler.workers.run_workers"

echo.
echo ========================================
echo  服务已启动 (队列已清空):
echo  - Flask: http://localhost:5000
echo  - RabbitMQ: http://localhost:15672
echo  - 默认账号: admin / admin123
echo ========================================
pause
