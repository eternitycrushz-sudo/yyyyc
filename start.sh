#!/bin/bash
echo "========================================"
echo " 抖音电商热点数据可视化分析系统"
echo "========================================"

# 检查 RabbitMQ
echo "[1] 检查 RabbitMQ..."
if ! docker ps | grep -q rabbitmq; then
    echo "    启动 RabbitMQ..."
    docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
    sleep 10
else
    echo "    RabbitMQ 已运行"
fi

# 启动 Flask 后端
echo "[2] 启动 Flask 后端..."
source .env/Scripts/activate
python backend/app.py &

# 启动爬虫 Workers
echo "[3] 启动爬虫 Workers..."
python crawler/workers/run_workers.py &

echo ""
echo "========================================"
echo " 服务已启动:"
echo " - Flask: http://localhost:5000"
echo " - RabbitMQ: http://localhost:15672"
echo " - 默认账号: admin / admin123"
echo "========================================"