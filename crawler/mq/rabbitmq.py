# -*- coding: utf-8 -*-
"""
RabbitMQ 连接和操作封装

原理讲解：
1. pika 是 Python 操作 RabbitMQ 的官方库
2. BlockingConnection 是同步阻塞连接，简单易用
3. channel 是通道，所有操作都通过通道进行
4. queue_declare 声明队列，durable=True 表示队列持久化（重启不丢失）
5. basic_publish 发送消息
6. basic_consume 消费消息
"""

import pika
import json
from typing import Callable, Any, Dict
from logger import get_logger

log = get_logger("RabbitMQ")


class RabbitMQClient:
    """
    RabbitMQ 客户端封装
    
    使用示例：
        # 发送消息
        client = RabbitMQClient()
        client.publish('my_queue', {'key': 'value'})
        
        # 消费消息
        def handler(message):
            print(message)
        client.consume('my_queue', handler)
    """
    
    def __init__(self, host: str = 'localhost', port: int = 5672,
                 username: str = 'guest', password: str = 'guest',
                 virtual_host: str = '/'):
        """
        初始化连接参数
        
        Args:
            host: RabbitMQ 服务器地址
            port: 端口，默认 5672
            username: 用户名，默认 guest
            password: 密码，默认 guest
            virtual_host: 虚拟主机，默认 /
        """
        self.credentials = pika.PlainCredentials(username, password)
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=virtual_host,
            credentials=self.credentials,
            # 心跳检测，防止长时间无操作断开
            heartbeat=600,
            # 连接超时
            blocked_connection_timeout=300
        )
        self._connection = None
        self._channel = None
    
    def _get_channel(self):
        """
        获取通道（懒加载）
        
        原理：
        - 连接(Connection)是 TCP 连接，比较重
        - 通道(Channel)是连接内的虚拟连接，轻量
        - 一个连接可以有多个通道
        - 我们复用连接和通道，避免频繁创建
        """
        if self._connection is None or self._connection.is_closed:
            self._connection = pika.BlockingConnection(self.parameters)
            self._channel = None
        
        if self._channel is None or self._channel.is_closed:
            self._channel = self._connection.channel()
        
        return self._channel
    
    def declare_queue(self, queue_name: str, durable: bool = True):
        """
        声明队列
        
        Args:
            queue_name: 队列名称
            durable: 是否持久化，True 表示 RabbitMQ 重启后队列还在
        
        原理：
        - 声明是幂等操作，队列存在就用，不存在就创建
        - durable=True 队列持久化
        - 但消息也要设置 delivery_mode=2 才能持久化
        """
        channel = self._get_channel()
        channel.queue_declare(queue=queue_name, durable=durable)
        log.debug(f"队列 {queue_name} 已声明")
    
    def publish(self, queue_name: str, message: Dict[str, Any]):
        """
        发送消息到队列
        
        Args:
            queue_name: 队列名称
            message: 消息内容（字典，会自动转 JSON）
        
        原理：
        - exchange='' 使用默认交换机，直接路由到队列
        - routing_key 就是队列名
        - delivery_mode=2 消息持久化
        """
        channel = self._get_channel()
        
        # 确保队列存在
        self.declare_queue(queue_name)
        
        # 发送消息
        channel.basic_publish(
            exchange='',  # 默认交换机
            routing_key=queue_name,  # 路由到这个队列
            body=json.dumps(message, ensure_ascii=False),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 消息持久化
                content_type='application/json'
            )
        )
        log.debug(f"消息已发送到 {queue_name}")
    
    def consume(self, queue_name: str, handler: Callable[[Dict], None],
                prefetch_count: int = 1):
        """
        消费队列消息（阻塞）
        
        Args:
            queue_name: 队列名称
            handler: 消息处理函数，接收字典参数
            prefetch_count: 预取数量，1 表示一次只取一条，处理完再取下一条
        
        原理：
        - basic_qos 设置预取，防止一个 Worker 抢太多消息
        - basic_consume 注册回调函数
        - start_consuming 开始阻塞等待消息
        - basic_ack 确认消息已处理，RabbitMQ 才会删除
        - basic_nack 拒绝消息，requeue=True 重新入队
        """
        channel = self._get_channel()
        
        # 确保队列存在
        self.declare_queue(queue_name)
        
        # 设置预取数量
        channel.basic_qos(prefetch_count=prefetch_count)
        
        def callback(ch, method, properties, body):
            """内部回调，处理消息"""
            try:
                message = json.loads(body)
                log.info(f"收到消息: {queue_name}")
                
                # 调用用户的处理函数
                handler(message)
                
                # 确认消息已处理
                ch.basic_ack(delivery_tag=method.delivery_tag)
                log.debug(f"消息处理完成: {queue_name}")
                
            except Exception as e:
                log.error(f"消息处理失败: {e}")
                # 拒绝消息，重新入队（会重试）
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # 注册消费者
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        
        log.info(f"开始消费队列: {queue_name}")
        
        # 开始阻塞等待消息
        channel.start_consuming()
    
    def close(self):
        """关闭连接"""
        if self._connection and self._connection.is_open:
            self._connection.close()
            log.info("RabbitMQ 连接已关闭")


# 全局单例，方便使用
_default_client = None

def get_mq_client() -> RabbitMQClient:
    """获取默认的 MQ 客户端"""
    global _default_client
    if _default_client is None:
        _default_client = RabbitMQClient()
    return _default_client


def publish(queue_name: str, message: Dict[str, Any]):
    """快捷发送消息"""
    get_mq_client().publish(queue_name, message)


def consume(queue_name: str, handler: Callable[[Dict], None]):
    """快捷消费消息"""
    get_mq_client().consume(queue_name, handler)
