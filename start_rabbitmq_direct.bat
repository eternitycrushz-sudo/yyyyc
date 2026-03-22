@echo off
chcp 65001 >nul
title RabbitMQ Server

set ERLANG_HOME=C:\Program Files\Erlang OTP
set PATH=%ERLANG_HOME%\bin;%PATH%
set ERL_LIBS=C:\Program Files\RabbitMQ Server\rabbitmq_server-4.0.5\plugins
set ERL_MAX_ETS_TABLES=50000
set ERL_MAX_PORTS=65536
set RABBITMQ_BASE=C:\Users\Z-M-Y\AppData\Roaming\RabbitMQ
set RABBITMQ_NODENAME=rabbit@Mingyue
set APPDATA=C:\Users\Z-M-Y\AppData\Roaming

echo.
echo  ==========================================
echo    启动 RabbitMQ Server（直接模式）
echo    Erlang: %ERLANG_HOME%\bin\erl.exe
echo  ==========================================
echo.

"C:\Program Files\RabbitMQ Server\rabbitmq_server-4.0.5\sbin\rabbitmq-server.bat"
