# -*- coding: utf-8 -*-
"""
CleanWorker - 数据清洗 Worker

原理讲解：
1. 可以作为独立 Worker 消费 clean_q 队列
2. 也可以直接调用 clean_all() 清洗所有未清洗数据
3. 每个 Handler 对应一个 Cleaner，自动匹配

消息格式（输入）：
{
    "task_id": "xxx",           # 任务ID（可选，不传则清洗所有）
    "handler": "goodsUserList"  # 指定清洗哪个接口（可选，不传则清洗所有）
}

使用方法：
    # 方式1：作为 Worker 消费队列
    worker = CleanWorker(db_config)
    worker.start()
    
    # 方式2：直接调用清洗
    worker = CleanWorker(db_config)
    worker.clean_all()  # 清洗所有
    worker.clean_handler('goodsUserList')  # 清洗指定接口
    worker.clean_task('task_123')  # 清洗指定任务
"""

import time
from typing import Dict, Any, List, Optional

from logger import get_logger
from crawler.workers.cleaners import ALL_CLEANERS


# 清洗队列名称
QUEUE_CLEAN = 'clean_q'


class CleanWorker:
    """
    数据清洗 Worker
    
    特性：
    1. 支持队列消费模式
    2. 支持直接调用模式
    3. 自动匹配 Handler 对应的 Cleaner
    4. 支持按任务/按接口清洗
    """
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'Dy@analysis2024',
            'database': 'dy_analysis_system'
        }
        
        self.log = get_logger('CleanWorker')
        
        # 初始化所有 Cleaner
        self.cleaners = {}
        for name, cleaner_class in ALL_CLEANERS.items():
            try:
                self.cleaners[name] = cleaner_class(self.db_config)
            except Exception as e:
                self.log.error(f"初始化 {name} Cleaner 失败: {e}")
        
        self.log.info(f"CleanWorker 初始化完成，共 {len(self.cleaners)} 个 Cleaner")
    
    def clean_all(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        清洗所有未清洗的数据
        
        Args:
            batch_size: 每批处理数量
            
        Returns:
            {
                'total_processed': 1000,
                'total_failed': 5,
                'details': {
                    'goodsUserList': {'processed': 500, 'failed': 2},
                    ...
                }
            }
        """
        self.log.info("开始清洗所有未清洗数据...")
        
        results = {
            'total_processed': 0,
            'total_failed': 0,
            'details': {}
        }
        
        for name, cleaner in self.cleaners.items():
            try:
                self.log.info(f"清洗 {name}...")
                result = cleaner.process(batch_size=batch_size)
                
                results['details'][name] = {
                    'processed': result.get('processed', 0),
                    'failed': result.get('failed', 0)
                }
                results['total_processed'] += result.get('processed', 0)
                results['total_failed'] += result.get('failed', 0)
                
            except Exception as e:
                self.log.error(f"清洗 {name} 失败: {e}")
                results['details'][name] = {'error': str(e)}
        
        self.log.info(
            f"清洗完成: 成功 {results['total_processed']}, "
            f"失败 {results['total_failed']}"
        )
        
        return results
    
    def clean_handler(self, handler_name: str, task_id: str = None,
                      batch_size: int = 100) -> Dict[str, Any]:
        """
        清洗指定接口的数据
        
        Args:
            handler_name: 接口名称（如 'goodsUserList'）
            task_id: 任务ID（可选）
            batch_size: 每批处理数量
        """
        if handler_name not in self.cleaners:
            self.log.error(f"未知的 Handler: {handler_name}")
            return {'success': False, 'error': f'Unknown handler: {handler_name}'}
        
        cleaner = self.cleaners[handler_name]
        return cleaner.process(task_id=task_id, batch_size=batch_size)
    
    def clean_task(self, task_id: str, batch_size: int = 100) -> Dict[str, Any]:
        """
        清洗指定任务的所有数据
        
        Args:
            task_id: 任务ID
            batch_size: 每批处理数量
        """
        self.log.info(f"清洗任务 {task_id} 的所有数据...")
        
        results = {
            'task_id': task_id,
            'total_processed': 0,
            'total_failed': 0,
            'details': {}
        }
        
        for name, cleaner in self.cleaners.items():
            try:
                result = cleaner.process(task_id=task_id, batch_size=batch_size)
                
                results['details'][name] = {
                    'processed': result.get('processed', 0),
                    'failed': result.get('failed', 0)
                }
                results['total_processed'] += result.get('processed', 0)
                results['total_failed'] += result.get('failed', 0)
                
            except Exception as e:
                self.log.error(f"清洗 {name} 失败: {e}")
                results['details'][name] = {'error': str(e)}
        
        return results
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理队列消息
        
        消息格式：
        {
            "task_id": "xxx",           # 可选
            "handler": "goodsUserList"  # 可选
        }
        """
        task_id = message.get('task_id')
        handler_name = message.get('handler')
        
        if handler_name:
            # 清洗指定接口
            return self.clean_handler(handler_name, task_id=task_id)
        elif task_id:
            # 清洗指定任务
            return self.clean_task(task_id)
        else:
            # 清洗所有
            return self.clean_all()
    
    def start(self):
        """
        启动 Worker，消费 clean_q 队列
        """
        from crawler.mq.rabbitmq import consume
        
        self.log.info(f"CleanWorker 启动，监听队列: {QUEUE_CLEAN}")
        
        def handler(message):
            self.log.info(f"收到清洗任务: {message}")
            result = self.handle_message(message)
            self.log.info(f"清洗完成: {result}")

        consume(QUEUE_CLEAN, handler)


if __name__ == '__main__':
    """测试 CleanWorker"""
    import logging
    from logger import init_logger
    
    init_logger(log_dir="logs", log_level=logging.DEBUG)
    
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'Dy@analysis2024',
        'database': 'dy_analysis_system'
    }
    
    worker = CleanWorker(db_config)
    
    # 测试清洗 UserList
    print("\n=== 测试清洗 goodsUserList ===")
    result = worker.clean_handler('goodsUserList', batch_size=10)
    print(f"结果: {result}")
