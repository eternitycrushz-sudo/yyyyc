@echo off
chcp 65001 >nul
title 爬虫 Workers (无代理版本)

cd /d "%~dp0"

echo 启动爬虫 Workers (禁用代理)...
echo.

set PROXY_URL=
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=

.env\Scripts\python.exe -m crawler.workers.run_workers

pause
