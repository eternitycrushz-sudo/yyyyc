# -*- coding: utf-8 -*-
"""
定时任务路由 - 自动更新数据
"""

from flask import Blueprint, request, jsonify, g
from backend.utils.decorators import login_required, permission_required
from backend.config import Config
import logging
import time
import threading

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint('scheduler', __name__)

# 定时任务状态
_scheduler_state = {
    'enabled': False,
    'interval_minutes': 60,
    'last_run': None,
    'next_run': None,
    'running': False,
    'run_count': 0,
    'timer': None,
    'lock': threading.Lock(),
}


def _run_scheduled_crawl():
    """执行定时爬取任务"""
    state = _scheduler_state
    with state['lock']:
        if state['running']:
            logger.warning("上一次定时任务仍在运行，跳过")
            return
        state['running'] = True

    try:
        from crawler.mq.rabbitmq import RabbitMQClient
        from crawler.workers import QUEUE_LIST

        task = {
            'start_page': 1,
            'end_page': 5,
            'task_id': f"scheduled_{int(time.time())}",
            'created_by': 'scheduler'
        }

        mq = RabbitMQClient(**Config.get_mq_config())
        mq.publish(QUEUE_LIST, task)
        mq.close()

        state['run_count'] += 1
        state['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"定时爬取任务已发送: {task['task_id']}")

    except Exception as e:
        logger.error(f"定时爬取任务失败: {e}")
    finally:
        with state['lock']:
            state['running'] = False

        # 安排下一次执行
        if state['enabled']:
            _schedule_next()


def _schedule_next():
    """安排下一次定时任务"""
    state = _scheduler_state

    if state['timer']:
        state['timer'].cancel()

    interval = state['interval_minutes'] * 60
    timer = threading.Timer(interval, _run_scheduled_crawl)
    timer.daemon = True
    timer.start()
    state['timer'] = timer
    state['next_run'] = time.strftime(
        '%Y-%m-%d %H:%M:%S',
        time.localtime(time.time() + interval)
    )


@scheduler_bp.route('/status', methods=['GET'])
@login_required
@permission_required('crawler:view')
def get_scheduler_status():
    """获取定时任务状态"""
    state = _scheduler_state
    return jsonify({
        'success': True,
        'data': {
            'enabled': state['enabled'],
            'interval_minutes': state['interval_minutes'],
            'last_run': state['last_run'],
            'next_run': state['next_run'],
            'running': state['running'],
            'run_count': state['run_count'],
        }
    })


@scheduler_bp.route('/start', methods=['POST'])
@login_required
@permission_required('crawler:start')
def start_scheduler():
    """
    启动定时任务

    请求：
    {
        "interval_minutes": 60,
        "start_page": 1,
        "end_page": 5
    }
    """
    state = _scheduler_state

    if state['enabled']:
        return jsonify({'success': False, 'message': '定时任务已在运行中'}), 400

    data = request.json or {}
    interval = max(int(data.get('interval_minutes', 60)), 5)  # 最小5分钟
    state['interval_minutes'] = interval
    state['enabled'] = True

    # 立即执行一次
    threading.Thread(target=_run_scheduled_crawl, daemon=True).start()

    logger.info(f"定时任务已启动，间隔 {interval} 分钟")

    return jsonify({
        'success': True,
        'message': f'定时任务已启动，每 {interval} 分钟自动更新',
        'data': {
            'interval_minutes': interval,
            'enabled': True
        }
    })


@scheduler_bp.route('/stop', methods=['POST'])
@login_required
@permission_required('crawler:start')
def stop_scheduler():
    """停止定时任务"""
    state = _scheduler_state

    if not state['enabled']:
        return jsonify({'success': False, 'message': '定时任务未在运行'}), 400

    state['enabled'] = False
    if state['timer']:
        state['timer'].cancel()
        state['timer'] = None
    state['next_run'] = None

    logger.info("定时任务已停止")

    return jsonify({
        'success': True,
        'message': '定时任务已停止'
    })


@scheduler_bp.route('/update', methods=['POST'])
@login_required
@permission_required('crawler:start')
def update_scheduler():
    """
    更新定时任务配置

    请求：
    {
        "interval_minutes": 30
    }
    """
    state = _scheduler_state
    data = request.json or {}

    interval = max(int(data.get('interval_minutes', state['interval_minutes'])), 5)
    state['interval_minutes'] = interval

    # 如果正在运行，重新安排下一次
    if state['enabled']:
        _schedule_next()

    return jsonify({
        'success': True,
        'message': f'定时任务间隔已更新为 {interval} 分钟',
        'data': {
            'interval_minutes': interval
        }
    })
