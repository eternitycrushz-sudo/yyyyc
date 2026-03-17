@echo off
chcp 65001 >nul
echo ========================================
echo  抖音电商热点数据可视化分析系统
echo ========================================
echo.

echo [1] 检查 RabbitMQ...

echo.
echo [2] 启动 Flask 后端...
start "Flask Backend" cmd /k "cd /d %~dp0 && .env\Scripts\python.exe backend/app.py"

echo.
echo [3] 启动爬虫 Workers...
start "Crawler Workers" cmd /k "cd /d %~dp0 && .env\Scripts\python.exe -m crawler.workers.run_workers"

echo.
echo ========================================
echo  服务已启动:
echo  - Flask: http://localhost:5000
echo  - RabbitMQ: http://localhost:15672
echo  - 默认账号: admin / admin123
echo.
echo  提示: 如需清空队列，请使用 start_clean.bat
echo ========================================
pause