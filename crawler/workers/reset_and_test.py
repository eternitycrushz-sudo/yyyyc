# -*- coding: utf-8 -*-
"""
重置所有数据并重新测试完整流程

步骤：
1. 清空 RabbitMQ 队列
2. 删除所有 analysis 相关表
3. 重新爬取数据
4. 执行清洗
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pymysql
import requests
import time
import logging
from logger import init_logger, get_logger

init_logger(log_dir="logs", log_level=logging.INFO)
log = get_logger('ResetAndTest')

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'dy_analysis_system'
}

# 所有 analysis 相关表
TABLES_TO_DROP = [
    # 清洗后的表
    'analysis_goods_trend',
    'analysis_user_top',
    'analysis_user_list',
    'analysis_live_trend',
    'analysis_live_list',
    'analysis_live_relation',
    'analysis_video_sales',
    'analysis_video_list',
    'analysis_video_time',
    # 原始数据表
    'analysis_goods_trend_raw',
    'analysis_user_top_raw',
    'analysis_user_list_raw',
    'analysis_live_trend_raw',
    'analysis_live_list_raw',
    'analysis_live_relation_raw',
    'analysis_video_sales_raw',
    'analysis_video_list_raw',
    'analysis_video_time_raw',
    # 任务表
    'crawler_task',
    'crawler_task_detail',
]


def step1_purge_rabbitmq():
    """清空 RabbitMQ 队列"""
    print("\n" + "=" * 60)
    print("步骤1: 清空 RabbitMQ 队列")
    print("=" * 60)
    
    queues = ['list_q', 'detail_q', 'analysis_q']
    
    for queue in queues:
        try:
            # 使用 RabbitMQ HTTP API 清空队列
            url = f"http://localhost:15672/api/queues/%2F/{queue}/contents"
            response = requests.delete(url, auth=('guest', 'guest'))
            if response.status_code in [200, 204]:
                print(f"  ✓ 清空队列 {queue}")
            else:
                print(f"  ✗ 清空队列 {queue} 失败: {response.status_code}")
        except Exception as e:
            print(f"  ✗ 清空队列 {queue} 失败: {e}")


def step2_drop_tables():
    """删除所有 analysis 相关表"""
    print("\n" + "=" * 60)
    print("步骤2: 删除数据库表")
    print("=" * 60)
    
    conn = pymysql.connect(**DB_CONFIG, charset='utf8mb4')
    
    with conn.cursor() as cursor:
        for table in TABLES_TO_DROP:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
                print(f"  ✓ 删除表 {table}")
            except Exception as e:
                print(f"  ✗ 删除表 {table} 失败: {e}")
    
    conn.commit()
    conn.close()
    print("  数据库表清理完成")


def step3_crawl_analysis():
    """爬取分析数据"""
    print("\n" + "=" * 60)
    print("步骤3: 爬取分析数据")
    print("=" * 60)
    
    from crawler.workers.analysis_worker import AnalysisWorker
    
    # 测试商品ID
    goods_id = '3620889142579355421'
    task_id = f'test_full_{int(time.time())}'
    
    print(f"  商品ID: {goods_id}")
    print(f"  任务ID: {task_id}")
    
    # 创建 Worker 并直接调用
    worker = AnalysisWorker(db_config=DB_CONFIG, days=30)
    
    message = {
        'goods_id': goods_id,
        'product_id': goods_id,
        'task_id': task_id
    }
    
    print("  开始爬取...")
    result = worker.crawl(message)
    
    print(f"\n  爬取完成:")
    print(f"    成功: {result['success_count']}/{len(result['handlers'])}")
    print(f"    总记录: {result['total_records']}")
    
    for name, detail in result['handlers'].items():
        status = "✓" if detail.get('success') else "✗"
        count = detail.get('total_count', 0)
        print(f"    {status} {name}: {count} 条")
    
    return result


def step4_clean_data():
    """清洗数据"""
    print("\n" + "=" * 60)
    print("步骤4: 清洗数据")
    print("=" * 60)
    
    from crawler.workers.clean_worker import CleanWorker
    
    worker = CleanWorker(DB_CONFIG)
    result = worker.clean_all(batch_size=100)
    
    print(f"\n  清洗完成:")
    print(f"    成功: {result['total_processed']}")
    print(f"    失败: {result['total_failed']}")
    
    for name, detail in result['details'].items():
        if 'error' in detail:
            print(f"    ✗ {name}: {detail['error']}")
        else:
            status = "✓" if detail['failed'] == 0 else "!"
            print(f"    {status} {name}: 成功 {detail['processed']}, 失败 {detail['failed']}")
    
    return result


def step5_verify():
    """验证结果"""
    print("\n" + "=" * 60)
    print("步骤5: 验证结果")
    print("=" * 60)
    
    conn = pymysql.connect(**DB_CONFIG, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    
    # 检查各表数据量
    tables = [
        ('analysis_goods_trend_raw', 'analysis_goods_trend'),
        ('analysis_user_top_raw', 'analysis_user_top'),
        ('analysis_user_list_raw', 'analysis_user_list'),
        ('analysis_live_trend_raw', 'analysis_live_trend'),
        ('analysis_live_relation_raw', 'analysis_live_relation'),
    ]
    
    print("\n  表数据统计:")
    print(f"  {'原始表':<30} {'清洗表':<30} {'原始':<8} {'清洗':<8}")
    print("  " + "-" * 80)
    
    with conn.cursor() as cursor:
        for raw_table, clean_table in tables:
            raw_count = 0
            clean_count = 0
            
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {raw_table}")
                raw_count = cursor.fetchone()['cnt']
            except:
                pass
            
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {clean_table}")
                clean_count = cursor.fetchone()['cnt']
            except:
                pass
            
            print(f"  {raw_table:<30} {clean_table:<30} {raw_count:<8} {clean_count:<8}")
    
    conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("完整流程测试")
    print("=" * 60)
    
    # 步骤1: 清空队列
    step1_purge_rabbitmq()
    
    # 步骤2: 删除表
    step2_drop_tables()
    
    # 步骤3: 爬取数据
    step3_crawl_analysis()
    
    # 步骤4: 清洗数据
    step4_clean_data()
    
    # 步骤5: 验证
    step5_verify()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
