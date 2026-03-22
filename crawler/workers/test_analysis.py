# -*- coding: utf-8 -*-
"""
AnalysisWorker 测试脚本

测试内容：
1. TaskManager 任务管理
2. 单个 Handler 测试
3. 完整 AnalysisWorker 流程测试

使用方式：
    cd 项目根目录
    python -m crawler.workers.test_analysis
"""

import sys
import os
import time

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from logger import init_logger, get_logger
import logging

init_logger(log_dir="logs", log_level=logging.DEBUG)
log = get_logger("TestAnalysis")

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Dy@analysis2024',
    'database': 'dy_analysis_system'
}

# 测试商品ID
TEST_GOODS_ID = '3620889142579355421'


def test_task_manager():
    """测试 TaskManager"""
    print("\n" + "=" * 50)
    print("测试 1: TaskManager 任务管理")
    print("=" * 50)
    
    from crawler.workers.task_manager import TaskManager, TaskStatus
    
    tm = TaskManager(DB_CONFIG)
    
    # 创建任务
    task_id = f"test_task_{int(time.time())}"
    tm.create_task(
        task_id=task_id,
        task_type='test',
        params={'test_key': 'test_value'},
        created_by='test_user',
        total_steps=3
    )
    print(f"✓ 创建任务: {task_id}")
    
    # 更新状态
    tm.update_status(task_id, TaskStatus.RUNNING)
    print("✓ 更新状态为 RUNNING")
    
    # 添加步骤
    tm.add_detail(task_id, 'step_1', 'completed', result={'count': 10})
    tm.add_detail(task_id, 'step_2', 'completed', result={'count': 20})
    tm.add_detail(task_id, 'step_3', 'failed', error_msg='测试错误')
    print("✓ 添加 3 个步骤")
    
    # 更新进度
    tm.update_progress(task_id, completed_steps=2, total_steps=3)
    print("✓ 更新进度")
    
    # 查询任务
    task = tm.get_task(task_id)
    print(f"✓ 查询任务: status={task['status']}, progress={task['progress']}%")
    
    # 查询步骤
    details = tm.get_task_details(task_id)
    print(f"✓ 查询步骤: {len(details)} 条")
    
    # 完成任务
    tm.complete_task(task_id, result={'total': 30})
    print("✓ 完成任务")
    
    print("\nTaskManager 测试通过 ✓")
    return True


def test_single_handler():
    """测试单个 Handler"""
    print("\n" + "=" * 50)
    print("测试 2: 单个 Handler (GoodsTrendHandler)")
    print("=" * 50)
    
    from crawler.workers.handlers.kol_handlers import GoodsTrendHandler
    from datetime import datetime, timedelta
    
    handler = GoodsTrendHandler(db_config=DB_CONFIG)
    
    # 计算时间范围
    now = datetime.now()
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(days=30)).timestamp() * 1000)
    
    task_id = f"test_handler_{int(time.time())}"
    
    print(f"商品ID: {TEST_GOODS_ID}")
    print(f"时间范围: {start_time} - {end_time}")
    print("开始爬取...")
    
    result = handler.fetch(
        goods_id=TEST_GOODS_ID,
        start_time=start_time,
        end_time=end_time,
        task_id=task_id
    )
    
    print(f"\n结果:")
    print(f"  - success: {result.get('success')}")
    print(f"  - total_count: {result.get('total_count')}")
    print(f"  - pages: {result.get('pages')}")
    print(f"  - raw_ids: {result.get('raw_ids')}")
    
    if result.get('success'):
        print("\n单个 Handler 测试通过 ✓")
    else:
        print(f"\n单个 Handler 测试失败: {result.get('error')}")
    
    return result.get('success', False)


def test_paged_handler():
    """测试分页 Handler"""
    print("\n" + "=" * 50)
    print("测试 3: 分页 Handler (GoodsUserListHandler)")
    print("=" * 50)
    
    from crawler.workers.handlers.kol_handlers import GoodsUserListHandler
    from datetime import datetime, timedelta
    
    handler = GoodsUserListHandler(db_config=DB_CONFIG)
    
    now = datetime.now()
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(days=30)).timestamp() * 1000)
    
    task_id = f"test_paged_{int(time.time())}"
    
    print(f"商品ID: {TEST_GOODS_ID}")
    print(f"is_paged: {handler.is_paged}")
    print("开始爬取（会自动翻页）...")
    
    result = handler.fetch(
        goods_id=TEST_GOODS_ID,
        start_time=start_time,
        end_time=end_time,
        task_id=task_id
    )
    
    print(f"\n结果:")
    print(f"  - success: {result.get('success')}")
    print(f"  - total_count: {result.get('total_count')}")
    print(f"  - pages: {result.get('pages')} (自动翻页)")
    print(f"  - raw_ids: {result.get('raw_ids')}")
    
    if result.get('success'):
        print("\n分页 Handler 测试通过 ✓")
    else:
        print(f"\n分页 Handler 测试失败: {result.get('error')}")
    
    return result.get('success', False)


def test_analysis_worker():
    """测试完整 AnalysisWorker"""
    print("\n" + "=" * 50)
    print("测试 4: 完整 AnalysisWorker 流程")
    print("=" * 50)
    
    from crawler.workers.analysis_worker import AnalysisWorker
    
    worker = AnalysisWorker(db_config=DB_CONFIG, days=30)
    
    task_id = f"test_full_{int(time.time())}"
    
    message = {
        'product_id': TEST_GOODS_ID,
        'goods_id': TEST_GOODS_ID,
        'task_id': task_id,
        'created_by': 'test_user'
    }
    
    print(f"任务ID: {task_id}")
    print(f"商品ID: {TEST_GOODS_ID}")
    print("开始执行（9个接口）...")
    print("-" * 30)
    
    # 直接调用 crawl 方法（不通过 MQ）
    result = worker.crawl(message)
    
    print("-" * 30)
    print(f"\n汇总结果:")
    print(f"  - 成功接口: {result.get('success_count')}/9")
    print(f"  - 失败接口: {result.get('fail_count')}/9")
    print(f"  - 总记录数: {result.get('total_records')}")
    
    print("\n各接口详情:")
    for name, data in result.get('handlers', {}).items():
        status = "✓" if data.get('success') else "✗"
        count = data.get('total_count', 0)
        pages = data.get('pages', 0)
        print(f"  {status} {name}: {count} 条, {pages} 页")
    
    # 查询任务状态
    from crawler.workers.task_manager import TaskManager
    tm = TaskManager(DB_CONFIG)
    task = tm.get_task(task_id)
    
    print(f"\n任务状态:")
    print(f"  - status: {task['status']}")
    print(f"  - progress: {task['progress']}%")
    
    if result.get('success_count', 0) > 0:
        print("\nAnalysisWorker 测试通过 ✓")
        return True
    else:
        print("\nAnalysisWorker 测试失败")
        return False


def test_via_mq():
    """通过 MQ 测试（需要先启动 Worker）"""
    print("\n" + "=" * 50)
    print("测试 5: 通过 MQ 发送任务")
    print("=" * 50)
    
    from crawler.mq.rabbitmq import publish
    from crawler.workers import QUEUE_ANALYSIS
    
    task_id = f"test_mq_{int(time.time())}"
    
    message = {
        'product_id': TEST_GOODS_ID,
        'goods_id': TEST_GOODS_ID,
        'task_id': task_id,
        'created_by': 'test_user'
    }
    
    print(f"发送任务到 {QUEUE_ANALYSIS}...")
    print(f"任务ID: {task_id}")
    
    try:
        publish(QUEUE_ANALYSIS, message)
        print("✓ 任务已发送")
        print("\n请在另一个终端启动 Worker:")
        print("  python -m crawler.workers.run_workers --worker analysis")
        return True
    except Exception as e:
        print(f"✗ 发送失败: {e}")
        print("请确保 RabbitMQ 已启动")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  AnalysisWorker 测试套件")
    print("=" * 60)
    
    results = {}
    
    # 测试 1: TaskManager
    try:
        results['TaskManager'] = test_task_manager()
    except Exception as e:
        print(f"✗ TaskManager 测试异常: {e}")
        results['TaskManager'] = False
    
    # 测试 2: 单个 Handler
    try:
        results['SingleHandler'] = test_single_handler()
    except Exception as e:
        print(f"✗ SingleHandler 测试异常: {e}")
        results['SingleHandler'] = False
    
    # 测试 3: 分页 Handler
    try:
        results['PagedHandler'] = test_paged_handler()
    except Exception as e:
        print(f"✗ PagedHandler 测试异常: {e}")
        results['PagedHandler'] = False
    
    # 测试 4: 完整流程
    try:
        results['AnalysisWorker'] = test_analysis_worker()
    except Exception as e:
        print(f"✗ AnalysisWorker 测试异常: {e}")
        import traceback
        traceback.print_exc()
        results['AnalysisWorker'] = False
    
    # 测试 5: MQ（可选）
    print("\n是否测试 MQ 发送? (y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            results['MQ'] = test_via_mq()
    except:
        pass
    
    # 汇总
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\n  总计: {passed_count}/{total_count} 通过")
    print("=" * 60)


if __name__ == '__main__':
    main()
