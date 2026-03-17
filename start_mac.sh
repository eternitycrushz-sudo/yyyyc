#!/bin/bash
echo "========================================"
echo " 抖音电商热点数据可视化分析系统"
echo " macOS 启动脚本"
echo "========================================"

cd "$(dirname "$0")"

# Step 1: 检查并启动 Docker 容器
echo ""
echo "[1] 检查 Docker 服务..."
if ! command -v docker &> /dev/null; then
    echo "    Docker 未安装，请先安装 Docker Desktop"
    echo "    brew install --cask docker"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "    Docker 未启动，正在打开 Docker Desktop..."
    open -a Docker
    echo "    等待 Docker 启动（最多60秒）..."
    for i in $(seq 1 60); do
        if docker info &> /dev/null 2>&1; then
            echo "    Docker 已启动"
            break
        fi
        sleep 1
    done
    if ! docker info &> /dev/null; then
        echo "    Docker 启动超时，请手动打开 Docker Desktop 后重试"
        exit 1
    fi
fi

# Step 2: 启动 MySQL + RabbitMQ
echo ""
echo "[2] 启动 MySQL + RabbitMQ 容器..."
docker compose up -d 2>&1

# 等待 MySQL 就绪
echo "    等待 MySQL 就绪..."
for i in $(seq 1 30); do
    if docker exec dy_mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
        echo "    MySQL 已就绪"
        break
    fi
    sleep 2
done

# 等待 RabbitMQ 就绪
echo "    等待 RabbitMQ 就绪..."
for i in $(seq 1 30); do
    if docker exec dy_rabbitmq rabbitmq-diagnostics check_running 2>/dev/null | grep -q "fully booted"; then
        echo "    RabbitMQ 已就绪"
        break
    fi
    sleep 2
done

# Step 3: 启动 Flask 后端
echo ""
echo "[3] 启动 Flask 后端..."
if [ -d "venv_mac" ]; then
    PYTHON="./venv_mac/bin/python3"
else
    PYTHON="python3"
fi

$PYTHON backend/app.py &
FLASK_PID=$!

echo ""
echo "========================================"
echo " 服务已启动:"
echo " - Flask:    http://localhost:5001"
echo " - 前端首页:  http://localhost:5001/"
echo " - 仪表盘:   http://localhost:5001/dashboard.html"
echo " - 热点预测:  http://localhost:5001/prediction.html"
echo " - RabbitMQ: http://localhost:15672 (guest/guest)"
echo " - 默认账号:  admin / admin123"
echo " - Flask PID: $FLASK_PID"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止 Flask 服务"
echo "停止容器: docker compose down"
echo ""

wait $FLASK_PID
