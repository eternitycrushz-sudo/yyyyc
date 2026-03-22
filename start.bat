@echo off
chcp 65001 >nul
title 抖音电商分析系统 - 启动器
color 0B

echo.
echo  ==========================================
echo     抖音电商热点数据可视化分析系统
echo     一键启动脚本 (Flask + Workers)
echo  ==========================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: ============================================
:: [1] 检查虚拟环境
:: ============================================
echo [1/4] 检查 Python 虚拟环境...
if not exist ".env\Scripts\python.exe" (
    echo.
    echo  [错误] 未找到虚拟环境 .env
    echo  请先运行 setup_env.bat 初始化环境
    echo.
    pause
    exit /b 1
)
echo       √ 虚拟环境已就绪

:: ============================================
:: [2] 检查 MySQL 连接
:: ============================================
echo [2/4] 检查 MySQL 连接...
.env\Scripts\python.exe -c "import pymysql; conn=pymysql.connect(host='localhost',port=3306,user='root',password='Dy@analysis2024',database='dy_analysis_system',connect_timeout=3); conn.close(); print('      √ MySQL 连接正常')" 2>nul
if errorlevel 1 (
    echo       [警告] MySQL 连接失败，请确认:
    echo         - MySQL 服务已启动
    echo         - 密码与 config.py 中的 DB_PASSWORD 一致
    echo         - 数据库 dy_analysis_system 已创建
    echo.
    set /p "CONTINUE=是否继续启动？(y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
)

:: ============================================
:: [3] 检查 RabbitMQ 连接
:: ============================================
echo [3/4] 检查 RabbitMQ 连接...
.env\Scripts\python.exe -c "import pika; conn=pika.BlockingConnection(pika.ConnectionParameters('localhost',5672,credentials=pika.PlainCredentials('guest','guest'),connection_attempts=1,retry_delay=0,socket_timeout=3)); conn.close(); print('      √ RabbitMQ 连接正常')" 2>nul
if errorlevel 1 (
    echo       [警告] RabbitMQ 连接失败，爬虫功能将不可用
    echo         - 确认 RabbitMQ 服务已启动
    echo         - 管理界面: http://localhost:15672
    echo.
)

:: ============================================
:: [4] 启动服务
:: ============================================
echo [4/4] 启动服务...
echo.

:: 启动 Flask 后端
echo       启动 Flask 后端 (端口 5001)...
start "Flask 后端 - 端口 5001" cmd /k "cd /d %~dp0 && title Flask 后端 - 端口 5001 && color 0A && .env\Scripts\python.exe backend/app.py 2>&1 | tee logs/flask.log"

:: 等待后端启动
timeout /t 2 /nobreak >nul

:: 启动爬虫 Workers
echo       启动爬虫 Workers (7个进程)...
start "爬虫 Workers" cmd /k "cd /d %~dp0 && title 爬虫 Workers && color 0E && .env\Scripts\python.exe -m crawler.workers.run_workers 2>&1 | tee logs/workers.log"

:: 等待 Workers 启动
timeout /t 2 /nobreak >nul

:: 自动打开浏览器
echo       打开浏览器...
start http://localhost:5001

:: ============================================
:: 启动完成
:: ============================================
echo.
echo  ==========================================
echo    所有服务已启动！
echo  ------------------------------------------
echo.
echo    Web 界面:  http://localhost:5001
echo    RabbitMQ:  http://localhost:15672
echo.
echo    默认账号:  admin
echo    默认密码:  admin123
echo.
echo    提示: 关闭此窗口不会停止服务
echo    如需停止，请关闭 Flask 和 Workers 窗口
echo  ==========================================
echo.
pause