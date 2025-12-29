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
    
    def __init__(self, mq_host: str = 'localhost', mq_port: int = 5672):
        """
        初始化 Worker
        
        Args:
            mq_host: RabbitMQ 地址
            mq_port: RabbitMQ 端口
        """
        self.mq_client = RabbitMQClient(host=mq_host, port=mq_port)
        self.log = get_logger(self.__class__.__name__)
        
        if not self.queue_name:
            raise ValueError(f"{self.__class__.__name__} 必须定义 queue_name")
    
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
        try:
            self.log.info(f"开始处理消息: {message}")
            
            # 1. 爬取
            raw_data = self.crawl(message)
            if raw_data is None:
                self.log.warning("爬取返回空数据，跳过")
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
            
            self.log.info("消息处理完成")
            
        except Exception as e:
            self.log.error(f"处理消息失败: {e}")
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
        self.mq_client.consume(self.queue_name, self.handle)
    
    def stop(self):
        """停止 Worker"""
        self.mq_client.close()
        self.log.info("Worker 已停止")
