# -*- coding: utf-8 -*-
"""
Worker 启动脚本

原理讲解：
1. 每个 Worker 是一个独立的消费者进程
2. 使用多进程（multiprocessing）同时运行多个 Worker
3. 每个 Worker 监听自己的队列，互不干扰
4. 可以根据需要启动多个相同类型的 Worker 来提高并发

使用方式：
    # 启动所有 Worker
    python run_workers.py
    
    # 只启动指定 Worker
    python run_workers.py --worker list
    python run_workers.py --worker detail
    python run_workers.py --worker analysis

架构图：
    ┌─────────────────────────────────────────────────────────┐
    │                    RabbitMQ Server                       │
    │  ┌─────────┐    ┌──────────┐    ┌───────────────┐       │
    │  │ list_q  │    │ detail_q │    │  analysis_q   │       │
    │  └────┬────┘    └────┬─────┘    └───────┬───────┘       │
    └───────┼──────────────┼──────────────────┼───────────────┘
            │              │                  │
            v              v                  v
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │  ListWorker   │ │ DetailWorker  │ │AnalysisWorker │
    │  (进程 1)     │ │  (进程 2)     │ │  (进程 3)     │
    └───────────────┘ └───────────────┘ └───────────────┘
"""

import argparse
import multiprocessing
import signal
import sys
from typing import List

from logger import init_logger, get_logger
import logging

# 初始化日志
init_logger(log_dir="logs", log_level=logging.DEBUG)
log = get_logger("WorkerRunner")

# 从配置文件读取
from config import get_config
_config = get_config()

DB_CONFIG = _config.get_db_config()
MQ_CONFIG = {
    'mq_host': _config.MQ_HOST,
    'mq_port': _config.MQ_PORT
}


def run_list_worker():
    """运行 ListWorker"""
    from crawler.workers.list_worker import ListWorker
    
    log.info("启动 ListWorker...")
    worker = ListWorker(db_config=DB_CONFIG, **MQ_CONFIG)
    worker.start()


def run_detail_worker():
    """运行 DetailWorker"""
    from crawler.workers.detail_worker import DetailWorker
    
    log.info("启动 DetailWorker...")
    worker = DetailWorker(db_config=DB_CONFIG, **MQ_CONFIG)
    worker.start()


def run_analysis_worker():
    """运行 AnalysisWorker"""
    from crawler.workers.analysis_worker import AnalysisWorker
    
    log.info("启动 AnalysisWorker...")
    worker = AnalysisWorker(db_config=DB_CONFIG, days=30, **MQ_CONFIG)
    worker.start()


# Worker 映射
WORKER_MAP = {
    'list': run_list_worker,
    'detail': run_detail_worker,
    'analysis': run_analysis_worker
}


def start_workers(worker_names: List[str] = None):
    """
    启动指定的 Worker
    
    原理：
    1. 使用 multiprocessing.Process 创建子进程
    2. 每个子进程运行一个 Worker
    3. 主进程等待所有子进程
    4. 支持 Ctrl+C 优雅退出
    
    Args:
        worker_names: 要启动的 Worker 名称列表，None 表示全部启动
    """
    if worker_names is None:
        worker_names = list(WORKER_MAP.keys())
    
    processes = []
    
    log.info(f"准备启动 Worker: {worker_names}")
    
    for name in worker_names:
        if name not in WORKER_MAP:
            log.warning(f"未知的 Worker: {name}")
            continue
        
        # 创建子进程
        p = multiprocessing.Process(
            target=WORKER_MAP[name],
            name=f"Worker-{name}"
        )
        p.start()
        processes.append(p)
        log.info(f"Worker {name} 已启动 (PID: {p.pid})")
    
    # 设置信号处理，支持 Ctrl+C 退出
    def signal_handler(signum, frame):
        log.info("收到退出信号，正在停止所有 Worker...")
        for p in processes:
            p.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 等待所有进程
    log.info("所有 Worker 已启动，按 Ctrl+C 退出")
    for p in processes:
        p.join()


def send_test_task():
    """
    发送测试任务到 list_q
    
    这是整个流程的入口：
    1. 发送任务到 list_q
    2. ListWorker 处理后发送到 detail_q
    3. DetailWorker 处理后发送到 analysis_q
    4. AnalysisWorker 处理完成
    """
    from crawler.mq.rabbitmq import publish
    from crawler.workers import QUEUE_LIST
    
    task = {
        'start_page': 1,
        'end_page': 2,  # 测试只爬2页
        'task_id': f'test_{int(__import__("time").time())}'
    }
    
    log.info(f"发送测试任务: {task}")
    publish(QUEUE_LIST, task)
    log.info("测试任务已发送到 list_q")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Worker 启动脚本')
    parser.add_argument(
        '--worker', '-w',
        choices=['list', 'detail', 'analysis', 'all'],
        default='all',
        help='要启动的 Worker 类型'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='发送测试任务'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # 只发送测试任务
        send_test_task()
    else:
        # 启动 Worker
        if args.worker == 'all':
            start_workers()
        else:
            start_workers([args.worker])
