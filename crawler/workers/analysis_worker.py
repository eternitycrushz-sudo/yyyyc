# -*- coding: utf-8 -*-
"""
AnalysisWorker - 数据分析爬取 Worker（重构版）

改进点：
1. 分页接口自动爬取所有页
2. 每个接口独立 Handler 处理
3. 集成 TaskManager 任务管理
4. 原始数据存入 *_raw 表
5. 支持事务回滚

消息格式（输入）：
{
    "product_id": "3620889142579355421",
    "goods_id": "3620889142579355421",
    "task_id": "xxx"
}
"""

import time
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from crawler.workers.base import BaseWorker
from crawler.workers import QUEUE_ANALYSIS
from crawler.workers.task_manager import TaskManager, TaskStatus
from crawler.workers.handlers import ALL_HANDLERS


class AnalysisWorker(BaseWorker):
    """
    数据分析 Worker（重构版）
    
    特性：
    1. 使用独立 Handler 处理每个接口
    2. 分页接口自动翻页
    3. 任务状态追踪
    4. 原始数据与清洗数据分离
    """
    
    queue_name = QUEUE_ANALYSIS
    next_queue = None  # 最后一层
    
    def __init__(self, db_config: Dict = None, days: int = 30, **kwargs):
        super().__init__(**kwargs)
        
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'Dy@analysis2024',
            'database': 'dy_analysis_system'
        }
        
        self.days = days
        
        # 初始化任务管理器
        self.task_manager = TaskManager(self.db_config)
        
        # 初始化所有 Handler
        self.handlers = {}
        for name, handler_class in ALL_HANDLERS.items():
            self.handlers[name] = handler_class(
                db_config=self.db_config,
                task_manager=self.task_manager
            )
        
        self.log.info(f"AnalysisWorker 初始化完成，共 {len(self.handlers)} 个 Handler")
    
    def _get_time_range(self) -> tuple:
        """获取查询时间范围"""
        now = datetime.now()
        end_time = int(now.timestamp() * 1000)
        start_time = int((now - timedelta(days=self.days)).timestamp() * 1000)
        return start_time, end_time
    
    def crawl(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        爬取所有分析接口

        注意：不操作 crawler_task 主表的状态和进度，
        避免多个 AnalysisWorker 并发覆盖同一个 task_id 导致进度乱跳。
        只记录子步骤到 crawler_task_detail 表。
        """
        goods_id = message.get('goods_id')
        task_id = message.get('task_id')

        if not goods_id:
            self.log.error("消息中缺少 goods_id")
            return None

        self.log.info(f"开始爬取商品分析数据: goods_id={goods_id}, task_id={task_id}")

        # 获取时间范围
        start_time, end_time = self._get_time_range()

        # 存储结果
        results = {
            'goods_id': goods_id,
            'task_id': task_id,
            'start_time': start_time,
            'end_time': end_time,
            'handlers': {},
            'success_count': 0,
            'fail_count': 0,
            'total_records': 0
        }

        # 依次调用每个 Handler
        for handler_name, handler in self.handlers.items():
            try:
                self.log.info(f"执行 Handler: {handler_name}")

                # 随机延迟（短延迟，防止触发风控）
                time.sleep(random.uniform(0.1, 0.3))

                # 调用 Handler
                result = handler.fetch(
                    goods_id=goods_id,
                    start_time=start_time,
                    end_time=end_time,
                    task_id=task_id
                )

                results['handlers'][handler_name] = result

                if result.get('success'):
                    results['success_count'] += 1
                    results['total_records'] += result.get('total_count', 0)
                else:
                    results['fail_count'] += 1

            except Exception as e:
                self.log.error(f"Handler {handler_name} 执行异常: {e}")
                results['fail_count'] += 1
                results['handlers'][handler_name] = {
                    'success': False,
                    'error': str(e)
                }

        self.log.info(
            f"分析数据爬取完成: 成功 {results['success_count']}/{len(self.handlers)}, "
            f"共 {results['total_records']} 条记录"
        )

        # 如果 API 没有返回有效数据，自动生成模拟数据
        if results['total_records'] == 0:
            self._generate_mock_if_needed(goods_id)

        return results
    
    def _generate_mock_if_needed(self, goods_id: str):
        """当 API 无数据时，自动生成模拟分析数据"""
        try:
            import pymysql
            conn = pymysql.connect(
                **self.db_config, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            cursor = conn.cursor()

            # 检查是否已有数据
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM analysis_goods_trend WHERE goods_id = %s",
                (goods_id,)
            )
            if cursor.fetchone()['cnt'] > 0:
                conn.close()
                return

            # 获取商品价格
            cursor.execute(
                "SELECT price FROM goods_list WHERE product_id = %s",
                (goods_id,)
            )
            row = cursor.fetchone()
            price = float(row['price']) if row and row['price'] else 10.0
            cursor.close()

            from backend.utils.mock_data import generate_mock_data_for_product
            generate_mock_data_for_product(conn, goods_id, price)
            self.log.info(f"已为商品 {goods_id} 生成模拟分析数据")
            conn.close()
        except Exception as e:
            self.log.error(f"生成模拟数据失败: {e}")

    def clean(self, data: Dict) -> Dict:
        """
        数据清洗（预留接口）
        
        清洗逻辑已解耦，这里只返回原始数据。
        清洗由独立的 CleanWorker 处理（消费 clean_q 队列）
        """
        return data
    
    def save(self, data: Dict, message: Dict[str, Any]):
        """
        保存已在各 Handler 中完成，这里不需要额外操作
        """
        pass
    
    def get_next_tasks(self, data: Dict, message: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        可以发送到清洗队列（可选）
        
        如果需要独立的清洗流程，可以在这里发送到 clean_q
        """
        # 暂时不发送到清洗队列
        # 后续可以添加：
        # return [{'queue': 'clean_q', 'data': {'task_id': data['task_id'], ...}}]
        return None


if __name__ == '__main__':
    """测试 AnalysisWorker"""
    from crawler.mq.rabbitmq import publish
    from logger import init_logger
    import logging
    
    init_logger(log_dir="logs", log_level=logging.DEBUG)
    
    # 发送测试任务
    test_task = {
        'product_id': '3620889142579355421',
        'goods_id': '3620889142579355421',
        'task_id': f'analysis_test_{int(time.time())}'
    }
    
    print("发送测试任务到 analysis_q...")
    publish(QUEUE_ANALYSIS, test_task)
    print("任务已发送，启动 Worker...")
    
    # 启动 Worker
    worker = AnalysisWorker(
        db_config={
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'Dy@analysis2024',
            'database': 'dy_analysis_system'
        },
        days=30
    )
    worker.start()
