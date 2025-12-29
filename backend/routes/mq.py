# -*- coding: utf-8 -*-
"""
消息队列路由
"""

from flask import Blueprint, request, jsonify, g
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.config import Config
from backend.utils.decorators import login_required, permission_required
from crawler.mq.rabbitmq import RabbitMQClient
from crawler.workers import QUEUE_LIST, QUEUE_DETAIL, QUEUE_ANALYSIS

mq_bp = Blueprint('mq', __name__)


@mq_bp.route('/send_task', methods=['POST'])
@login_required
@permission_required('crawler:start')
def send_mq_task():
    """
    发送任务到消息队列
    
    请求：
    {
        "queue": "list_q",
        "task": {"start_page": 1, "end_page": 10}
    }
    """
    data = request.json or {}
    queue_name = data.get('queue', QUEUE_LIST)
    task = data.get('task', {})
    
    task['task_id'] = f"web_{g.current_user['user_id']}_{int(time.time())}"
    task['created_by'] = g.current_user['username']
    
    try:
        mq = RabbitMQClient(**Config.get_mq_config())
        mq.publish(queue_name, task)
        mq.close()
        
        return jsonify({
            'success': True,
            'message': f'任务已发送到 {queue_name}',
            'data': {'task_id': task['task_id']}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@mq_bp.route('/start_list_crawler', methods=['POST'])
@login_required
@permission_required('crawler:start')
def start_list_crawler():
    """
    启动商品列表爬取任务
    
    请求：
    {
        "start_page": 1,
        "end_page": 10
    }
    """
    data = request.json or {}
    
    task = {
        'start_page': int(data.get('start_page', 1)),
        'end_page': int(data.get('end_page', 1)),
        'task_id': f"list_{g.current_user['user_id']}_{int(time.time())}",
        'created_by': g.current_user['username']
    }
    
    try:
        mq = RabbitMQClient(**Config.get_mq_config())
        mq.publish(QUEUE_LIST, task)
        mq.close()
        
        return jsonify({
            'success': True,
            'message': '列表爬取任务已发送',
            'data': {
                'task_id': task['task_id'],
                'note': '请确保 Worker 进程已启动'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@mq_bp.route('/start_detail_crawler', methods=['POST'])
@login_required
@permission_required('crawler:start')
def start_detail_crawler():
    """
    启动商品详情爬取任务
    
    请求：
    {
        "product_id": "3620889142579355421"
    }
    """
    data = request.json or {}
    product_id = data.get('product_id')
    
    if not product_id:
        return jsonify({'success': False, 'message': '缺少 product_id'}), 400
    
    task = {
        'product_id': str(product_id),
        'task_id': f"detail_{g.current_user['user_id']}_{int(time.time())}",
        'created_by': g.current_user['username']
    }
    
    try:
        mq = RabbitMQClient(**Config.get_mq_config())
        mq.publish(QUEUE_DETAIL, task)
        mq.close()
        
        return jsonify({
            'success': True,
            'message': '详情爬取任务已发送',
            'data': {'task_id': task['task_id']}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@mq_bp.route('/start_analysis', methods=['POST'])
@login_required
@permission_required('crawler:start')
def start_analysis():
    """
    启动数据分析爬取任务
    
    请求：
    {
        "goods_id": "3620889142579355421"
    }
    """
    data = request.json or {}
    goods_id = data.get('goods_id')
    
    if not goods_id:
        return jsonify({'success': False, 'message': '缺少 goods_id'}), 400
    
    task = {
        'product_id': str(goods_id),
        'goods_id': str(goods_id),
        'task_id': f"analysis_{g.current_user['user_id']}_{int(time.time())}",
        'created_by': g.current_user['username']
    }
    
    try:
        mq = RabbitMQClient(**Config.get_mq_config())
        mq.publish(QUEUE_ANALYSIS, task)
        mq.close()
        
        return jsonify({
            'success': True,
            'message': '分析任务已发送',
            'data': {'task_id': task['task_id']}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500
