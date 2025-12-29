# -*- coding: utf-8 -*-
"""
爬虫路由
"""

from flask import Blueprint, request, jsonify, g
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.decorators import login_required, permission_required

crawler_bp = Blueprint('crawler', __name__)

# 爬虫状态
crawler_status = {
    'running': False,
    'total_pages': 0,
    'current_page': 0
}


@crawler_bp.route('/start', methods=['POST'])
@login_required
@permission_required('crawler:start')
def start_crawler():
    """启动爬虫（直接模式，非MQ）"""
    if crawler_status['running']:
        return jsonify({'success': False, 'message': '爬虫正在运行中'}), 400
    
    # 这里可以启动爬虫任务
    # 为了简化，暂时返回提示使用 MQ 模式
    return jsonify({
        'success': True,
        'message': '请使用 /api/mq/start_list_crawler 接口启动爬虫任务'
    })


@crawler_bp.route('/status', methods=['GET'])
@login_required
@permission_required('crawler:view')
def get_status():
    """获取爬虫状态"""
    return jsonify({
        'success': True,
        'data': crawler_status
    })


@crawler_bp.route('/stop', methods=['POST'])
@login_required
@permission_required('crawler:stop')
def stop_crawler():
    """停止爬虫"""
    return jsonify({
        'success': False,
        'message': '暂不支持停止'
    })


# ============================================
# 数据清洗相关接口
# ============================================

@crawler_bp.route('/clean/all', methods=['POST'])
@login_required
@permission_required('crawler:clean')
def clean_all_data():
    """
    清洗所有未清洗的数据
    
    POST /api/crawler/clean/all
    Body: {
        "batch_size": 100  // 可选，每批处理数量
    }
    """
    from crawler.workers.clean_worker import CleanWorker
    
    data = request.get_json() or {}
    batch_size = data.get('batch_size', 100)
    
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'dy_analysis_system'
    }
    
    try:
        worker = CleanWorker(db_config)
        result = worker.clean_all(batch_size=batch_size)
        
        return jsonify({
            'success': True,
            'message': f"清洗完成: 成功 {result['total_processed']}, 失败 {result['total_failed']}",
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清洗失败: {str(e)}'
        }), 500


@crawler_bp.route('/clean/handler/<handler_name>', methods=['POST'])
@login_required
@permission_required('crawler:clean')
def clean_handler_data(handler_name):
    """
    清洗指定接口的数据
    
    POST /api/crawler/clean/handler/goodsUserList
    Body: {
        "task_id": "xxx",  // 可选，指定任务
        "batch_size": 100  // 可选
    }
    """
    from crawler.workers.clean_worker import CleanWorker
    
    data = request.get_json() or {}
    task_id = data.get('task_id')
    batch_size = data.get('batch_size', 100)
    
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'dy_analysis_system'
    }
    
    try:
        worker = CleanWorker(db_config)
        result = worker.clean_handler(handler_name, task_id=task_id, batch_size=batch_size)
        
        return jsonify({
            'success': result.get('success', True),
            'message': f"清洗完成: 成功 {result.get('processed', 0)}, 失败 {result.get('failed', 0)}",
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清洗失败: {str(e)}'
        }), 500


@crawler_bp.route('/clean/task/<task_id>', methods=['POST'])
@login_required
@permission_required('crawler:clean')
def clean_task_data(task_id):
    """
    清洗指定任务的所有数据
    
    POST /api/crawler/clean/task/task_123
    Body: {
        "batch_size": 100  // 可选
    }
    """
    from crawler.workers.clean_worker import CleanWorker
    
    data = request.get_json() or {}
    batch_size = data.get('batch_size', 100)
    
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'dy_analysis_system'
    }
    
    try:
        worker = CleanWorker(db_config)
        result = worker.clean_task(task_id, batch_size=batch_size)
        
        return jsonify({
            'success': True,
            'message': f"清洗完成: 成功 {result['total_processed']}, 失败 {result['total_failed']}",
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清洗失败: {str(e)}'
        }), 500


@crawler_bp.route('/clean/status', methods=['GET'])
@login_required
@permission_required('crawler:view')
def get_clean_status():
    """
    获取清洗状态（各表未清洗数据量）
    
    GET /api/crawler/clean/status
    """
    import pymysql
    
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'dy_analysis_system'
    }
    
    # 原始数据表列表
    raw_tables = [
        'analysis_goods_trend_raw',
        'analysis_user_top_raw',
        'analysis_user_list_raw',
        'analysis_live_trend_raw',
        'analysis_live_list_raw',
        'analysis_live_relation_raw',
        'analysis_video_sales_raw',
        'analysis_video_list_raw',
        'analysis_video_time_raw',
    ]
    
    try:
        conn = pymysql.connect(**db_config, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        status = {}
        
        with conn.cursor() as cursor:
            for table in raw_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as total, SUM(is_cleaned=0) as uncleaned FROM {table}")
                    row = cursor.fetchone()
                    status[table] = {
                        'total': row['total'] or 0,
                        'uncleaned': int(row['uncleaned'] or 0),
                        'cleaned': (row['total'] or 0) - int(row['uncleaned'] or 0)
                    }
                except:
                    status[table] = {'error': '表不存在'}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取状态失败: {str(e)}'
        }), 500
