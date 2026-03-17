# -*- coding: utf-8 -*-
"""
测试数据清洗模块

使用方法：
    source .env/Scripts/activate
    python -m crawler.workers.test_cleaner
"""

import logging
from logger import init_logger, get_logger

# 初始化日志
init_logger(log_dir="logs", log_level=logging.INFO)
log = get_logger('TestCleaner')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Dy@analysis2024',
    'database': 'dy_analysis_system'
}


def test_clean_all():
    """清洗所有接口的数据"""
    from crawler.workers.clean_worker import CleanWorker
    
    print("\n" + "=" * 60)
    print("清洗所有接口数据")
    print("=" * 60)
    
    worker = CleanWorker(DB_CONFIG)
    result = worker.clean_all(batch_size=100)
    
    print(f"\n总计: 成功 {result['total_processed']}, 失败 {result['total_failed']}")
    print("\n各接口详情:")
    for name, detail in result['details'].items():
        if 'error' in detail:
            print(f"  ✗ {name}: {detail['error']}")
        else:
            print(f"  ✓ {name}: 成功 {detail['processed']}, 失败 {detail['failed']}")
    
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("数据清洗测试")
    print("=" * 60)
    
    # 清洗所有接口
    test_clean_all()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
