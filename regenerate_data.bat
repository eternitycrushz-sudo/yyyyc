@echo off
chcp 65001 >nul
title Regenerate Analysis Data

echo.
echo =========================================
echo   重新生成分析数据
echo =========================================
echo.
echo 这个脚本会清空所有分析数据表
echo 后端会自动生成新数据（使用当前日期）
echo.

echo [1/2] 连接 MySQL...

REM 运行 SQL 脚本
mysql -u root -p"Dy@analysis2024" < regenerate_data.sql

if errorlevel 1 (
    echo.
    echo [错误] MySQL 连接失败
    echo 请确认：
    echo - MySQL 服务已启动
    echo - 密码正确
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] 数据清理完成
echo.
echo 重新启动 Flask 后端以生成新数据：
echo 1. 关闭 start.bat 窗口
echo 2. 重新运行 start.bat
echo 3. 访问商品详情页面
echo 4. 后端会自动生成最新的分析数据
echo.
echo =========================================
echo   完成！请重启 Flask 后端
echo =========================================
echo.
pause
