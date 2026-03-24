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
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    SHOP_SEARCH_PATH = "/api/douke/search"

    @classmethod
    def _get_token(cls):
        from crawler.token_manager import get_token
        return get_token()
    
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
    
    # 多种搜索类型，获取不同类型的商品
    # search_type: 1=爆款推荐, 2=实时热销, 3=达人热推, 5=高佣好物, 8=潜力爆品, 11=综合推荐
    SEARCH_TYPES = [
        ('11', '综合推荐'),
        ('1', '爆款推荐'),
        ('2', '实时热销'),
        ('5', '高佣好物'),
        ('8', '潜力爆品'),
        ('3', '达人热推'),
    ]

    def crawl(self, message: Dict[str, Any]) -> List[Dict]:
        """
        爬取商品列表

        原理：
        1. 从消息中获取页码范围
        2. 使用 6 种搜索类型逐页爬取，获取不同类型的商品
        3. 按 product_id 去重后返回

        Args:
            message: 包含 start_page, end_page 的消息

        Returns:
            所有页的商品数据列表（已去重）
        """
        start_page = message.get('start_page', 1)
        end_page = message.get('end_page', 1)

        self.log.info(f"开始爬取商品列表: 第{start_page}页 - 第{end_page}页, 共{len(self.SEARCH_TYPES)}种搜索类型")

        seen_ids = set()
        all_products = []

        for search_type, type_name in self.SEARCH_TYPES:
            self.log.info(f"--- 搜索类型: {type_name} (search_type={search_type}) ---")
            empty_count = 0

            for page in range(start_page, end_page + 1):
                try:
                    time.sleep(random.uniform(0.3, 0.6))

                    result = self._fetch_page(page, search_type=search_type)

                    if result and 'data' in result and result['data']:
                        products = result['data']
                        new_count = 0
                        for p in products:
                            pid = p.get('product_id') or p.get('id')
                            if pid and pid not in seen_ids:
                                seen_ids.add(pid)
                                all_products.append(p)
                                new_count += 1
                        self.log.info(f"[{type_name}] 第{page}页: {len(products)}条, 新增{new_count}条")
                        empty_count = 0
                    else:
                        self.log.warning(f"[{type_name}] 第{page}页数据为空")
                        empty_count += 1
                        if empty_count >= 2:
                            break

                except Exception as e:
                    self.log.error(f"[{type_name}] 第{page}页爬取失败: {e}")
                    continue

        self.log.info(f"商品列表爬取完成，共{len(all_products)}条不重复数据")
        return all_products
    
    def _fetch_page(self, page: int, search_type: str = '11') -> Dict:
        """
        爬取单页数据（API 限制每页最多 10 条）

        原理：
        1. 构造请求参数
        2. 使用 ReduxSigner 生成签名
        3. 发送请求获取数据
        """
        params = {
            'page': str(page),
            'limit': '10',
            'sell_num_min': '1000',
            'search_type': search_type,
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
            self._get_token()
        )
        
        # 构造 URL 参数
        query_params = params.copy()
        query_params['sign'] = signer['url_sign']
        query_params['time'] = signer['timestamp']
        
        # 发送请求（禁用代理和SSL验证，解决连接问题）
        url = f"{ReduxSigner.BASE_URL}{self.SHOP_SEARCH_PATH}"
        try:
            session = requests.Session()
            session.trust_env = False
            # 明确禁用所有代理
            session.proxies = {}
            adapter = requests.adapters.HTTPAdapter(max_retries=0)
            https_adapter = requests.adapters.HTTPAdapter(max_retries=0)
            session.mount('http://', adapter)
            session.mount('https://', https_adapter)
            response = session.get(url, params=query_params, headers=headers, timeout=30, proxies={}, verify=False)
            return response.json()
        except requests.exceptions.SSLError as e:
            self.log.error(f"SSL 错误，尝试使用代理禁用方案: {e}")
            # 最后的手段：直接使用 requests 而不是 session
            response = requests.get(url, params=query_params, headers=headers, timeout=30, proxies={}, verify=False)
            return response.json()
    
    def clean(self, data: List[Dict]) -> List[Dict]:
        """
        数据清洗

        清洗规则：
        1. 过滤无效记录（无 product_id 或无标题）
        2. 字段类型转换（价格转 float，数量转 int）
        3. 空值填充默认值
        4. 去除标题首尾空白和特殊字符
        5. 价格异常值过滤（负数、超大值）
        """
        if not data:
            return data

        cleaned = []
        for item in data:
            # 过滤无效记录
            pid = item.get('product_id') or item.get('id')
            title = item.get('title', '')
            if not pid or not title:
                continue

            # 清洗标题：去首尾空白
            item['title'] = title.strip()

            # 价格类型转换与校验
            for field in ['price', 'coupon', 'coupon_price', 'cos_fee', 'kol_cos_fee']:
                val = item.get(field)
                if val is not None:
                    try:
                        val = float(val)
                        if val < 0 or val > 999999:
                            val = 0
                        item[field] = val
                    except (ValueError, TypeError):
                        item[field] = 0

            # 比例字段转换
            for field in ['cos_ratio', 'kol_cos_ratio', 'subsidy_ratio', 'butie_rate']:
                val = item.get(field)
                if val is not None:
                    try:
                        item[field] = float(val)
                    except (ValueError, TypeError):
                        item[field] = 0

            # 整数字段转换
            for field in ['view_num', 'order_count', 'combined', 'kol_weekday']:
                val = item.get(field)
                if val is not None:
                    try:
                        item[field] = int(float(val))
                    except (ValueError, TypeError):
                        item[field] = 0

            # 空值填充
            item.setdefault('platform', 'douyin')
            item.setdefault('shop_name', '')
            item.setdefault('cover', '')
            item.setdefault('status', 1)

            cleaned.append(item)

        removed = len(data) - len(cleaned)
        if removed > 0:
            self.log.info(f"数据清洗: 原始{len(data)}条, 过滤{removed}条, 保留{len(cleaned)}条")

        return cleaned
    
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
        self.log.info(f"数据库配置: host={self.db_config.get('host')}, database={self.db_config.get('database')}")

        try:
            # 为每条数据补充 id 字段（如果缺少）
            processed_data = []
            for item in data:
                if 'id' not in item:
                    # 使用 product_id 作为 id
                    item['id'] = item.get('product_id', f"temp_{len(processed_data)}")
                processed_data.append(item)

            with DBCallback(**self.db_config) as db:
                self.log.info("DBCallback 连接成功")
                # 构造保存格式
                save_data = {'data': processed_data}
                db.save_page(1, save_data)

            self.log.info(f"数据保存成功，共{len(processed_data)}条")

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
