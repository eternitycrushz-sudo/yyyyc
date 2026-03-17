# -*- coding: utf-8 -*-
"""
Worker 基类

原理讲解：
1. Worker 是消费者，从队列取消息并处理
2. 每个 Worker 监听一个队列
3. 处理流程：爬取 → 清洗 → 入库 → 发送下一个队列
4. 使用模板方法模式，子类只需实现具体的爬取/清洗/入库逻辑
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from crawler.mq.rabbitmq import RabbitMQClient, publish
from logger import get_logger
import pymysql


class BaseWorker(ABC):
    """
    Worker 基类
    
    子类需要实现：
    - queue_name: 监听的队列名
    - crawl(): 爬取数据
    - clean(): 清洗数据（可选，默认不处理）
    - save(): 保存数据
    - get_next_tasks(): 返回要发送到下一个队列的任务（可选）
    
    使用示例：
        class MyWorker(BaseWorker):
            queue_name = 'my_queue'
            
            def crawl(self, message):
                return requests.get(...).json()
            
            def save(self, data):
                db.insert(data)
        
        worker = MyWorker()
        worker.start()  # 开始消费
    """
    
    # 子类必须定义监听的队列名
    queue_name: str = None
    
    # 下一个队列名（可选，用于链式调用）
    next_queue: str = None
    
    def __init__(self, mq_host: str = 'localhost', mq_port: int = 5672,
                 mq_user: str = 'guest', mq_password: str = 'guest'):
        """
        初始化 Worker

        Args:
            mq_host: RabbitMQ 地址
            mq_port: RabbitMQ 端口
            mq_user: RabbitMQ 用户名
            mq_password: RabbitMQ 密码
        """
        self.mq_client = RabbitMQClient(
            host=mq_host, port=mq_port,
            username=mq_user, password=mq_password
        )
        self.log = get_logger(self.__class__.__name__)
        
        if not self.queue_name:
            raise ValueError(f"{self.__class__.__name__} 必须定义 queue_name")
    
    def _update_task_log(self, task_id: str, status: str, result: str = ''):
        """回写任务状态到 crawler_task_log 表（状态只能前进不能回退）"""
        if not task_id or not hasattr(self, 'db_config'):
            return
        try:
            conn = pymysql.connect(**self.db_config, charset='utf8mb4')
            with conn.cursor() as cursor:
                # 状态只能前进：sent → running → completed/failed
                # 不允许从 completed/failed 回退到 running
                if status == 'running':
                    cursor.execute(
                        "UPDATE crawler_task_log SET status=%s WHERE task_id=%s AND status IN ('sent','running')",
                        (status, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE crawler_task_log SET status=%s, result=%s WHERE task_id=%s",
                        (status, result[:500] if result else '', task_id)
                    )
            conn.commit()
            conn.close()
        except Exception as e:
            self.log.debug(f"更新 task_log 状态失败(可忽略): {e}")

    def handle(self, message: Dict[str, Any]):
        """
        处理消息的完整流程

        流程：
        1. 爬取数据
        2. 清洗数据
        3. 保存数据
        4. 发送到下一个队列

        Args:
            message: 从队列收到的消息
        """
        task_id = message.get('task_id')
        try:
            self.log.info(f"开始处理消息: {message}")
            self._update_task_log(task_id, 'running')

            # 1. 爬取
            raw_data = self.crawl(message)
            if raw_data is None:
                self.log.warning("爬取返回空数据")
                # 即使爬取失败，也尝试发送到下一个队列（确保后续流程能执行）
                next_tasks = self.get_next_tasks(None, message)
                if next_tasks:
                    for task in next_tasks:
                        queue = task.get('queue', self.next_queue)
                        if queue:
                            publish(queue, task.get('data', task))
                            self.log.debug(f"已发送到队列: {queue}")
                self._update_task_log(task_id, 'completed', '无数据')
                return

            # 2. 清洗（预留接口，默认不处理）
            cleaned_data = self.clean(raw_data)

            # 3. 保存
            self.save(cleaned_data, message)

            # 4. 发送到下一个队列
            next_tasks = self.get_next_tasks(cleaned_data, message)
            if next_tasks:
                for task in next_tasks:
                    queue = task.get('queue', self.next_queue)
                    if queue:
                        publish(queue, task.get('data', task))
                        self.log.debug(f"已发送到队列: {queue}")

            data_count = len(cleaned_data) if isinstance(cleaned_data, list) else 1
            self._update_task_log(task_id, 'completed', f'成功处理 {data_count} 条数据')
            self.log.info("消息处理完成")

        except Exception as e:
            self.log.error(f"处理消息失败: {e}")
            self._update_task_log(task_id, 'failed', str(e))
            raise  # 抛出异常让 MQ 重试
    
    @abstractmethod
    def crawl(self, message: Dict[str, Any]) -> Any:
        """
        爬取数据（子类必须实现）
        
        Args:
            message: 从队列收到的消息，包含爬取所需的参数
            
        Returns:
            爬取到的原始数据
        """
        pass
    
    def clean(self, data: Any) -> Any:
        """
        清洗数据（子类可选实现）
        
        默认不做任何处理，直接返回原数据。
        子类可以覆盖此方法实现数据清洗逻辑。
        
        Args:
            data: 爬取到的原始数据
            
        Returns:
            清洗后的数据
        """
        # 预留接口，默认不处理
        return data
    
    @abstractmethod
    def save(self, data: Any, message: Dict[str, Any]):
        """
        保存数据（子类必须实现）
        
        Args:
            data: 清洗后的数据
            message: 原始消息（可能包含一些元数据如 product_id）
        """
        pass
    
    def get_next_tasks(self, data: Any, message: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        获取要发送到下一个队列的任务（子类可选实现）
        
        返回格式：
        [
            {'queue': 'next_queue_name', 'data': {...}},
            {'queue': 'another_queue', 'data': {...}},
        ]
        
        如果只发送到 self.next_queue，可以简化为：
        [
            {'product_id': '123'},
            {'product_id': '456'},
        ]
        
        Args:
            data: 处理后的数据
            message: 原始消息
            
        Returns:
            任务列表，None 表示不发送
        """
        return None
    
    def start(self):
        """
        启动 Worker，开始消费消息
        
        这是一个阻塞方法，会一直运行直到手动停止
        """
        self.log.info(f"Worker 启动，监听队列: {self.queue_name}")
        self.mq_client.consume(self.queue_name, self.handle, prefetch_count=3)
    
    def stop(self):
        """停止 Worker"""
        self.mq_client.close()
        self.log.info("Worker 已停止")
