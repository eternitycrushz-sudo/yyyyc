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
from backend.routes.oplog import log_operation
from backend.routes.notification import create_notification
import json

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

        _save_task_log(task['task_id'], 'list', json.dumps(task))
        log_operation('启动列表爬取', '爬虫', f"页码 {task['start_page']}-{task['end_page']}")

        return jsonify({
            'success': True,
            'message': '列表爬取任务已发送',
            'data': {
                'task_id': task['task_id'],
                'note': '请确保 Worker 进程已启动'
            }
        })
    except Exception as e:
        _save_task_log(task['task_id'], 'list', json.dumps(task), status='failed', result=str(e))
        log_operation('启动列表爬取', '爬虫', str(e), status=0)
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

        _save_task_log(task['task_id'], 'detail', json.dumps(task))
        log_operation('启动详情爬取', '爬虫', f"商品 {product_id}")

        return jsonify({
            'success': True,
            'message': '详情爬取任务已发送',
            'data': {'task_id': task['task_id']}
        })
    except Exception as e:
        _save_task_log(task['task_id'], 'detail', json.dumps(task), status='failed', result=str(e))
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@mq_bp.route('/start_batch_detail', methods=['POST'])
@login_required
@permission_required('crawler:start')
def start_batch_detail():
    """
    批量爬取所有商品的详情+分析

    从 goods_list 中取出所有 product_id，
    为每个商品发送 detail_q 和 analysis_q 任务。
    """
    from backend.models.base import get_db_connection

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id FROM goods_list")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return jsonify({'success': False, 'message': '商品列表为空，请先爬取商品列表'}), 400

        product_ids = [r['product_id'] for r in rows]
        ts = int(time.time())
        batch_task_id = f"batch_{g.current_user['user_id']}_{ts}"

        mq = RabbitMQClient(**Config.get_mq_config())
        sent = 0
        for i, pid in enumerate(product_ids):
            detail_task = {
                'product_id': str(pid),
                'task_id': f"detail_{g.current_user['user_id']}_{ts}_{i}",
                'created_by': g.current_user['username']
            }
            analysis_task = {
                'product_id': str(pid),
                'goods_id': str(pid),
                'task_id': f"analysis_{g.current_user['user_id']}_{ts}_{i}",
                'created_by': g.current_user['username']
            }
            mq.publish(QUEUE_DETAIL, detail_task)
            mq.publish(QUEUE_ANALYSIS, analysis_task)
            sent += 1
        mq.close()

        _save_task_log(batch_task_id, 'batch_detail',
                       json.dumps({'count': sent, 'product_ids': product_ids[:5]}))
        # 批量任务发送完成后直接标记为 completed（实际执行由各 Worker 独立处理）
        try:
            conn2 = get_db_connection()
            with conn2.cursor() as c2:
                c2.execute("UPDATE crawler_task_log SET status='completed', result=%s WHERE task_id=%s",
                           (f'已发送 {sent} 个商品的详情+分析任务', batch_task_id))
            conn2.commit()
            conn2.close()
        except Exception:
            pass
        log_operation('批量爬取详情+分析', '爬虫', f"共 {sent} 个商品")

        return jsonify({
            'success': True,
            'message': f'已为 {sent} 个商品发送详情爬取+数据分析任务',
            'data': {'task_id': batch_task_id, 'count': sent}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'批量发送失败: {str(e)}'
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

        _save_task_log(task['task_id'], 'analysis', json.dumps(task))
        log_operation('启动数据分析', '爬虫', f"商品 {goods_id}")

        return jsonify({
            'success': True,
            'message': '分析任务已发送',
            'data': {'task_id': task['task_id']}
        })
    except Exception as e:
        _save_task_log(task['task_id'], 'analysis', json.dumps(task), status='failed', result=str(e))
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


def _save_task_log(task_id, task_type, params, status='sent', result=''):
    """保存爬虫任务到数据库"""
    try:
        from backend.models.base import get_db_connection
        user_id = g.current_user.get('user_id') if hasattr(g, 'current_user') else None
        username = g.current_user.get('username') if hasattr(g, 'current_user') else None
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO crawler_task_log (task_id, task_type, params, user_id, username, status, result) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (task_id, task_type, params, user_id, username, status, result)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"保存任务日志失败: {e}")


@mq_bp.route('/task_logs', methods=['GET'])
@login_required
@permission_required('crawler:view')
def get_task_logs():
    """获取爬虫任务历史（合并发送记录和执行结果）"""
    try:
        from backend.models.base import get_db_connection
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM crawler_task_log")
        total = cursor.fetchone()['total']
        cursor.execute(
            "SELECT * FROM crawler_task_log ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (page_size, offset)
        )
        logs = cursor.fetchall()

        # 直接使用 crawler_task_log 自身的 status 和 result 作为执行状态
        for log_item in logs:
            log_status = log_item.get('status', 'sent')
            if log_status == 'sent':
                log_item['exec_status'] = 'pending'
                log_item['exec_progress'] = 0
            elif log_status == 'running':
                log_item['exec_status'] = 'running'
                log_item['exec_progress'] = 50
            elif log_status == 'completed':
                log_item['exec_status'] = 'completed'
                log_item['exec_progress'] = 100
            elif log_status == 'failed':
                log_item['exec_status'] = 'failed'
                log_item['exec_progress'] = 100
            else:
                log_item['exec_status'] = log_status
                log_item['exec_progress'] = 0
            log_item['exec_result'] = log_item.get('result', '')
            log_item['exec_error'] = None

        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {'list': logs, 'total': total, 'page': page, 'page_size': page_size}
        })
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500


@mq_bp.route('/task_detail/<task_id>', methods=['GET'])
@login_required
@permission_required('crawler:view')
def get_task_detail(task_id):
    """获取任务执行详情"""
    try:
        from backend.models.base import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # 从 crawler_task_log 获取任务信息（权威来源）
        task = None
        cursor.execute("SELECT * FROM crawler_task_log WHERE task_id = %s", (task_id,))
        log_row = cursor.fetchone()
        if log_row:
            log_status = log_row.get('status', 'sent')
            if log_status in ('completed', 'failed'):
                progress = 100
            elif log_status == 'running':
                progress = 50
            else:
                progress = 0
            task = {
                'task_id': log_row['task_id'],
                'task_type': log_row.get('task_type', ''),
                'status': log_status,
                'progress': progress,
                'result': log_row.get('result', ''),
                'error_msg': '' if log_status != 'failed' else log_row.get('result', ''),
                'created_by': log_row.get('username', ''),
                'started_at': str(log_row['created_at']) if log_row.get('created_at') else None,
                'completed_at': str(log_row['updated_at']) if log_row.get('updated_at') else None,
                'created_at': str(log_row['created_at']) if log_row.get('created_at') else None,
            }

        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {'task': task, 'details': []}
        })
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500
