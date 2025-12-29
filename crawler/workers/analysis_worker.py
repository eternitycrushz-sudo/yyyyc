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
            'password': '123456',
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
        
        流程：
        1. 创建/更新任务状态
        2. 依次调用每个 Handler
        3. 记录每个步骤的结果
        4. 汇总返回
        """
        goods_id = message.get('goods_id')
        task_id = message.get('task_id')
        
        if not goods_id:
            self.log.error("消息中缺少 goods_id")
            return None
        
        self.log.info(f"开始爬取商品分析数据: goods_id={goods_id}, task_id={task_id}")
        
        # 获取时间范围
        start_time, end_time = self._get_time_range()
        
        # 创建任务记录
        if task_id:
            self.task_manager.create_task(
                task_id=task_id,
                task_type='analysis',
                params={
                    'goods_id': goods_id,
                    'start_time': start_time,
                    'end_time': end_time
                },
                created_by=message.get('created_by'),
                total_steps=len(self.handlers)
            )
            self.task_manager.update_status(task_id, TaskStatus.RUNNING)
        
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
        
        completed_steps = 0
        
        # 依次调用每个 Handler
        for handler_name, handler in self.handlers.items():
            try:
                self.log.info(f"执行 Handler: {handler_name}")
                
                # 随机延迟
                time.sleep(random.uniform(0.5, 1))
                
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
                    
                    # 记录步骤成功
                    if task_id:
                        self.task_manager.add_detail(
                            task_id=task_id,
                            step_name=handler_name,
                            status='completed',
                            result={
                                'total_count': result.get('total_count', 0),
                                'pages': result.get('pages', 0)
                            }
                        )
                else:
                    results['fail_count'] += 1
                    
                    # 记录步骤失败
                    if task_id:
                        self.task_manager.add_detail(
                            task_id=task_id,
                            step_name=handler_name,
                            status='failed',
                            error_msg=result.get('error', '未知错误')
                        )
                
                completed_steps += 1
                
                # 更新进度
                if task_id:
                    self.task_manager.update_progress(
                        task_id=task_id,
                        completed_steps=completed_steps,
                        total_steps=len(self.handlers)
                    )
                    
            except Exception as e:
                self.log.error(f"Handler {handler_name} 执行异常: {e}")
                results['fail_count'] += 1
                results['handlers'][handler_name] = {
                    'success': False,
                    'error': str(e)
                }
                
                if task_id:
                    self.task_manager.add_detail(
                        task_id=task_id,
                        step_name=handler_name,
                        status='failed',
                        error_msg=str(e)
                    )
        
        # 更新任务最终状态
        if task_id:
            if results['fail_count'] == 0:
                self.task_manager.complete_task(task_id, result={
                    'success_count': results['success_count'],
                    'total_records': results['total_records']
                })
            elif results['success_count'] > 0:
                # 部分成功
                self.task_manager.update_status(
                    task_id, TaskStatus.COMPLETED,
                    progress=100
                )
            else:
                # 全部失败
                self.task_manager.fail_task(task_id, '所有接口爬取失败')
        
        self.log.info(
            f"分析数据爬取完成: 成功 {results['success_count']}/{len(self.handlers)}, "
            f"共 {results['total_records']} 条记录"
        )
        
        return results
    
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
            'password': '123456',
            'database': 'dy_analysis_system'
        },
        days=30
    )
    worker.start()
