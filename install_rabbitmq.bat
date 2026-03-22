@echo off
chcp 65001 >nul
title RabbitMQ 一键安装脚本
color 0B

echo.
echo  ==========================================
echo    RabbitMQ 一键安装脚本
echo  ==========================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 创建临时下载目录
if not exist "installer" mkdir installer

:: ============================================
:: [1] 检查是否已安装 Erlang
:: ============================================
echo [1/4] 检查 Erlang...
where erl >nul 2>nul
if not errorlevel 1 goto :ERLANG_OK

:: 检查常见安装路径
if exist "C:\Program Files\Erlang OTP\bin\erl.exe" goto :ERLANG_OK
if exist "C:\Program Files\erl-*\bin\erl.exe" goto :ERLANG_OK

echo       Erlang 未安装，开始下载...
echo       下载 Erlang OTP 26.2.5 (约100MB，请耐心等待)...
echo.
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/erlang/otp/releases/download/OTP-26.2.5.7/otp_win64_26.2.5.7.exe' -OutFile 'installer\otp_win64.exe' -UseBasicParsing}"
if not exist "installer\otp_win64.exe" goto :ERLANG_DOWNLOAD_FAIL

echo       下载完成，开始安装 Erlang...
echo       (安装窗口弹出后请点击 Next 完成安装，全部默认即可)
start /wait installer\otp_win64.exe /S
echo       √ Erlang 安装完成
goto :SET_ERLANG_HOME

:ERLANG_DOWNLOAD_FAIL
echo       [错误] Erlang 下载失败
echo       请手动下载: https://www.erlang.org/downloads
echo       安装完成后重新运行此脚本
pause
exit /b 1

:ERLANG_OK
echo       √ Erlang 已安装

:: 设置 ERLANG_HOME 环境变量
:SET_ERLANG_HOME
echo       设置 ERLANG_HOME 环境变量...
for /d %%i in ("C:\Program Files\Erlang OTP" "C:\Program Files\erl-*") do (
    if exist "%%i\bin\erl.exe" (
        setx ERLANG_HOME "%%i" >nul 2>nul
        set "ERLANG_HOME=%%i"
    )
)

:: ============================================
:: [2] 检查是否已安装 RabbitMQ
:: ============================================
echo [2/4] 检查 RabbitMQ...
where rabbitmqctl >nul 2>nul
if not errorlevel 1 goto :RABBITMQ_OK

if exist "C:\Program Files\RabbitMQ Server\rabbitmq_server-*\sbin\rabbitmqctl.bat" goto :RABBITMQ_OK

echo       RabbitMQ 未安装，开始下载...
echo       下载 RabbitMQ 4.0.5 (约15MB)...
echo.
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/rabbitmq/rabbitmq-server/releases/download/v4.0.5/rabbitmq-server-4.0.5.exe' -OutFile 'installer\rabbitmq-server.exe' -UseBasicParsing}"
if not exist "installer\rabbitmq-server.exe" goto :RABBITMQ_DOWNLOAD_FAIL

echo       下载完成，开始安装 RabbitMQ...
echo       (安装窗口弹出后请点击 Next 完成安装，全部默认即可)
start /wait installer\rabbitmq-server.exe /S
echo       √ RabbitMQ 安装完成
goto :ENABLE_PLUGIN

:RABBITMQ_DOWNLOAD_FAIL
echo       [错误] RabbitMQ 下载失败
echo       请手动下载: https://www.rabbitmq.com/install-windows.html
echo       安装完成后重新运行此脚本
pause
exit /b 1

:RABBITMQ_OK
echo       √ RabbitMQ 已安装

:: ============================================
:: [3] 启用管理插件
:: ============================================
:ENABLE_PLUGIN
echo [3/4] 启用 RabbitMQ 管理插件...

:: 找到 rabbitmq-plugins 命令
set "RABBIT_SBIN="
for /d %%i in ("C:\Program Files\RabbitMQ Server\rabbitmq_server-*") do set "RABBIT_SBIN=%%i\sbin"

if defined RABBIT_SBIN (
    "%RABBIT_SBIN%\rabbitmq-plugins.bat" enable rabbitmq_management >nul 2>nul
    echo       √ 管理插件已启用
) else (
    rabbitmq-plugins enable rabbitmq_management >nul 2>nul
    echo       √ 管理插件已启用
)

:: ============================================
:: [4] 启动服务
:: ============================================
echo [4/4] 启动 RabbitMQ 服务...
net start RabbitMQ >nul 2>nul
if not errorlevel 1 goto :STARTED

:: 如果 net start 失败，尝试用 rabbitmq-server 启动
if defined RABBIT_SBIN (
    start "RabbitMQ" "%RABBIT_SBIN%\rabbitmq-server.bat"
) else (
    start "RabbitMQ" rabbitmq-server
)
timeout /t 5 /nobreak >nul

:STARTED
:: 验证是否启动成功
powershell -Command "& {try { $r = Invoke-WebRequest -Uri 'http://localhost:15672' -UseBasicParsing -TimeoutSec 5; Write-Host '      √ RabbitMQ 启动成功' } catch { Write-Host '      [提示] RabbitMQ 可能仍在启动中，请稍等几秒后访问管理界面' }}"

:: ============================================
:: 完成
:: ============================================
echo.
echo  ==========================================
echo    安装完成！
echo  ------------------------------------------
echo    管理界面: http://localhost:15672
echo    用户名:   guest
echo    密码:     guest
echo    端口:     5672
echo  ==========================================
echo.

:: 清理下载文件
set /p "CLEAN=是否删除安装包？(y/n): "
if /i "%CLEAN%"=="y" (
    rd /s /q installer 2>nul
    echo  已清理安装包
)

pause