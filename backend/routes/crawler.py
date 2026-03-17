# -*- coding: utf-8 -*-
"""
爬虫路由
"""

from flask import Blueprint, request, jsonify, g
import threading
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.decorators import login_required, permission_required
from backend.config import Config

crawler_bp = Blueprint('crawler', __name__)

def _get_db_config():
    """从统一配置获取数据库连接信息"""
    return {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'database': Config.DB_NAME
    }

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
    
    db_config = _get_db_config()
    
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
    
    db_config = _get_db_config()
    
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
    
    db_config = _get_db_config()
    
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


# 表名 → handler 名称映射
_TABLE_TO_HANDLER = {
    'analysis_goods_trend_raw': 'goodsTrend',
    'analysis_user_top_raw': 'goodsUserTop',
    'analysis_user_list_raw': 'goodsUserList',
    'analysis_live_trend_raw': 'goodsLiveSalesTrend',
    'analysis_live_list_raw': 'goodsLiveList',
    'analysis_live_relation_raw': 'goodsLiveRelation',
    'analysis_video_sales_raw': 'goodsVideosales',
    'analysis_video_list_raw': 'goodsVideoList',
    'analysis_video_time_raw': 'goodsVideoTime',
}


@crawler_bp.route('/clean/table/<table_name>', methods=['POST'])
@login_required
@permission_required('crawler:clean')
def clean_table_data(table_name):
    """
    按表名清洗单张表的数据

    POST /api/crawler/clean/table/analysis_goods_trend_raw
    """
    from crawler.workers.clean_worker import CleanWorker

    handler_name = _TABLE_TO_HANDLER.get(table_name)
    if not handler_name:
        return jsonify({'success': False, 'message': f'未知的表: {table_name}'}), 400

    data = request.get_json() or {}
    batch_size = data.get('batch_size', 200)

    db_config = _get_db_config()

    try:
        worker = CleanWorker(db_config)
        result = worker.clean_handler(handler_name, batch_size=batch_size)

        return jsonify({
            'success': True,
            'message': f"{table_name} 清洗完成: 成功 {result.get('processed', 0)}, 失败 {result.get('failed', 0)}",
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
    
    db_config = _get_db_config()
    
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


# ============================================
# 代理配置相关接口
# ============================================

@crawler_bp.route('/proxy', methods=['GET'])
@login_required
@permission_required('crawler:view')
def get_proxy():
    """获取当前代理配置"""
    import os
    proxy_url = os.getenv('PROXY_URL', '')
    return jsonify({
        'success': True,
        'data': {'proxy_url': proxy_url}
    })


@crawler_bp.route('/proxy', methods=['POST'])
@login_required
@permission_required('crawler:start')
def set_proxy():
    """
    设置代理

    POST /api/crawler/proxy
    Body: { "proxy_url": "http://user:pass@host:port" }
    """
    import os
    data = request.get_json() or {}
    proxy_url = data.get('proxy_url', '').strip()

    os.environ['PROXY_URL'] = proxy_url

    # 同步更新 Config 类
    try:
        Config.PROXY_URL = proxy_url
    except Exception:
        pass

    return jsonify({
        'success': True,
        'message': f'代理已{"设置为 " + proxy_url if proxy_url else "清除"}'
    })


@crawler_bp.route('/proxy/test', methods=['POST'])
@login_required
@permission_required('crawler:start')
def test_proxy():
    """测试代理是否可用"""
    import os
    data = request.get_json() or {}
    proxy_url = data.get('proxy_url', '').strip() or os.getenv('PROXY_URL', '')

    if not proxy_url:
        return jsonify({'success': False, 'message': '未配置代理地址'}), 400

    proxies = {'http': proxy_url, 'https': proxy_url}

    try:
        # 测试连通性：通过代理访问目标网站
        resp = requests.get(
            'https://www.reduxingtui.com/',
            proxies=proxies,
            timeout=15,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/131.0.0.0 Safari/537.36'
            }
        )
        return jsonify({
            'success': resp.status_code == 200,
            'message': f'状态码: {resp.status_code}' + (' - 连接成功!' if resp.status_code == 200 else ' - 连接异常'),
            'data': {'status_code': resp.status_code}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'代理连接失败: {str(e)}'
        }), 500
