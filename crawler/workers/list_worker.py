# -*- coding: utf-8 -*-
"""
ListWorker - 商品列表爬取 Worker

原理讲解：
1. 这是消息队列的第一层 Worker
2. 从 list_q 队列接收任务（包含页码范围）
3. 爬取商品列表，保存到数据库
4. 将每个商品的 product_id 发送到 detail_q 队列

消息格式（输入）：
{
    "start_page": 1,
    "end_page": 10,
    "task_id": "xxx"  # 可选，用于追踪
}

消息格式（输出到 detail_q）：
{
    "product_id": "3620889142579355421",
    "task_id": "xxx"
}
"""

import time
import random
from typing import Dict, Any, List, Optional

from crawler.workers.base import BaseWorker
from crawler.workers import QUEUE_LIST, QUEUE_DETAIL
from crawler.dy_xingtui.ReduxSiger import ReduxSigner
from crawler.dy_xingtui.db_callback import DBCallback
import requests


class ListWorker(BaseWorker):
    """
    商品列表 Worker
    
    职责：
    1. 接收爬取任务（页码范围）
    2. 爬取商品列表数据
    3. 保存到数据库
    4. 将 product_id 发送到下一个队列
    """
    
    # 监听的队列
    queue_name = QUEUE_LIST
    
    # 下一个队列
    next_queue = QUEUE_DETAIL
    
    # API 配置
    TOKEN = "45114cedfddd64db6b0c5f0acf929487"
    SHOP_SEARCH_PATH = "/api/douke/search"
    
    def __init__(self, db_config: Dict = None, **kwargs):
        """
        初始化 ListWorker
        
        Args:
            db_config: 数据库配置，格式：
                {
                    'host': 'localhost',
                    'port': 3306,
                    'user': 'root',
                    'password': '123456',
                    'database': 'dy_analysis_system'
                }
            **kwargs: 传递给父类的参数（mq_host, mq_port）
        """
        super().__init__(**kwargs)
        
        # 数据库配置
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '123456',
            'database': 'dy_analysis_system'
        }
    
    def crawl(self, message: Dict[str, Any]) -> List[Dict]:
        """
        爬取商品列表
        
        原理：
        1. 从消息中获取页码范围
        2. 逐页爬取数据
        3. 返回所有商品数据
        
        Args:
            message: 包含 start_page, end_page 的消息
            
        Returns:
            所有页的商品数据列表
        """
        start_page = message.get('start_page', 1)
        end_page = message.get('end_page', 1)
        
        self.log.info(f"开始爬取商品列表: 第{start_page}页 - 第{end_page}页")
        
        all_products = []
        
        for page in range(start_page, end_page + 1):
            try:
                # 随机延迟，避免被封
                time.sleep(random.uniform(1, 1.5))
                
                # 爬取单页
                result = self._fetch_page(page)
                
                if result and 'data' in result and result['data']:
                    products = result['data']
                    all_products.extend(products)
                    self.log.info(f"第{page}页获取成功，{len(products)}条数据")
                else:
                    self.log.warning(f"第{page}页数据为空")
                    # 如果遇到空页，可能已经到末尾了
                    break
                    
            except Exception as e:
                self.log.error(f"第{page}页爬取失败: {e}")
                continue
        
        self.log.info(f"商品列表爬取完成，共{len(all_products)}条数据")
        return all_products
    
    def _fetch_page(self, page: int) -> Dict:
        """
        爬取单页数据
        
        原理：
        1. 构造请求参数
        2. 使用 ReduxSigner 生成签名
        3. 发送请求获取数据
        """
        params = {
            'page': str(page),
            'limit': '10',
            'sell_num_min': '1000',
            'search_type': '11',
            'sort_type': '1',
            'source': '0',
            'platform': 'douyin'
        }
        
        # 获取服务器时间戳
        ts = ReduxSigner.get_timestamp_by_server()
        
        # 生成签名
        signer = ReduxSigner.get_siger_by_params(params, ts)
        
        # 构造请求头
        headers = ReduxSigner.get_headers(
            signer['header_sign'], 
            signer['timestamp'], 
            self.TOKEN
        )
        
        # 构造 URL 参数
        query_params = params.copy()
        query_params['sign'] = signer['url_sign']
        query_params['time'] = signer['timestamp']
        
        # 发送请求
        url = f"{ReduxSigner.BASE_URL}{self.SHOP_SEARCH_PATH}"
        response = requests.get(url, params=query_params, headers=headers)
        
        return response.json()
    
    def clean(self, data: List[Dict]) -> List[Dict]:
        """
        数据清洗（预留接口）
        
        TODO: 在这里实现数据清洗逻辑
        - 字段类型转换
        - 空值处理
        - 数据校验
        
        Args:
            data: 原始商品数据列表
            
        Returns:
            清洗后的数据
        """
        # 预留接口，暂时直接返回
        # 后续可以在这里添加清洗逻辑
        return data
    
    def save(self, data: List[Dict], message: Dict[str, Any]):
        """
        保存数据到数据库
        
        原理：
        1. 使用 DBCallback 连接数据库
        2. 批量插入/更新数据
        3. 使用 INSERT ON DUPLICATE KEY UPDATE 实现增量更新
        
        Args:
            data: 清洗后的商品数据
            message: 原始消息
        """
        self.log.info(f"=== 进入 save 方法，数据条数: {len(data) if data else 0} ===")
        
        if not data:
            self.log.warning("没有数据需要保存")
            return
        
        self.log.info(f"开始保存{len(data)}条商品数据到数据库")
        self.log.info(f"数据库配置: {self.db_config}")
        
        try:
            with DBCallback(**self.db_config) as db:
                self.log.info("DBCallback 连接成功")
                # 模拟分页保存（DBCallback.save_page 需要 page 和 data 格式）
                # 这里我们直接构造一个假的响应格式
                fake_response = {'data': data}
                db.save_page(1, fake_response)
                
            self.log.info("数据保存成功")
            
        except Exception as e:
            self.log.error(f"数据保存失败: {e}")
            import traceback
            self.log.error(traceback.format_exc())
            raise
    
    def get_next_tasks(self, data: List[Dict], message: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        生成下一级任务
        
        原理：
        1. 从商品数据中提取 product_id
        2. 为每个商品生成一个详情爬取任务
        3. 任务会被发送到 detail_q 队列
        
        Args:
            data: 商品数据列表
            message: 原始消息（可能包含 task_id）
            
        Returns:
            任务列表，每个任务包含 product_id
        """
        if not data:
            return None
        
        tasks = []
        task_id = message.get('task_id')
        
        for product in data:
            # 提取 product_id
            product_id = product.get('product_id')
            if product_id:
                task = {
                    'product_id': str(product_id),
                    'task_id': task_id  # 传递任务ID，方便追踪
                }
                tasks.append(task)
        
        self.log.info(f"生成{len(tasks)}个详情爬取任务")
        return tasks


if __name__ == '__main__':
    """
    测试 ListWorker
    
    运行前确保：
    1. RabbitMQ 已启动
    2. 数据库已配置
    """
    from crawler.mq.rabbitmq import publish
    from logger import init_logger
    import logging
    
    init_logger(log_dir="logs", log_level=logging.DEBUG)
    
    # 发送一个测试任务到 list_q
    test_task = {
        'start_page': 1,
        'end_page': 2,
        'task_id': 'test_001'
    }
    
    print("发送测试任务到 list_q...")
    publish(QUEUE_LIST, test_task)
    print("任务已发送，启动 Worker...")
    
    # 启动 Worker
    worker = ListWorker(
        db_config={
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '123456',
            'database': 'dy_analysis_system'
        }
    )
    worker.start()
