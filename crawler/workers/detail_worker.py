# -*- coding: utf-8 -*-
"""
DetailWorker - 商品详情爬取 Worker

原理讲解：
1. 这是消息队列的第二层 Worker
2. 从 detail_q 队列接收任务（包含 product_id）
3. 调用 /api/douke/view 接口获取商品详情
4. 保存到数据库
5. 将 product_id 发送到 analysis_q 队列，触发分析数据爬取

消息格式（输入）：
{
    "product_id": "3620889142579355421",
    "task_id": "xxx"
}

消息格式（输出到 analysis_q）：
{
    "product_id": "3620889142579355421",
    "goods_id": "3620889142579355421",  # 分析接口用的是 goods_id
    "task_id": "xxx"
}
"""

import time
import random
from typing import Dict, Any, List, Optional

from crawler.workers.base import BaseWorker
from crawler.workers import QUEUE_DETAIL, QUEUE_ANALYSIS
from crawler.dy_xingtui.ReduxSiger import ReduxSigner
import requests
import pymysql


class DetailWorker(BaseWorker):
    """
    商品详情 Worker
    
    职责：
    1. 接收 product_id
    2. 爬取商品详情数据
    3. 保存到数据库
    4. 将任务发送到分析队列
    """
    
    # 监听的队列
    queue_name = QUEUE_DETAIL
    
    # 下一个队列
    next_queue = QUEUE_ANALYSIS
    
    # API 配置
    SHOP_VIEW_PATH = "/api/douke/view"

    @classmethod
    def _get_token(cls):
        from crawler.token_manager import get_token
        return get_token()
    
    def __init__(self, db_config: Dict = None, **kwargs):
        """
        初始化 DetailWorker
        
        Args:
            db_config: 数据库配置
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'Dy@analysis2024',
            'database': 'dy_analysis_system'
        }
        
        # 确保详情表存在
        self._ensure_table()
    
    def _ensure_table(self):
        """
        确保数据库表存在
        
        原理：
        - 使用 CREATE TABLE IF NOT EXISTS
        - 表结构根据 /api/douke/view 接口返回的字段设计
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS `product_detail` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `product_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
            `title` VARCHAR(500) COMMENT '商品标题',
            `cover` VARCHAR(500) COMMENT '封面图',
            `price` DECIMAL(10,2) COMMENT '价格',
            `commission_rate` DECIMAL(5,2) COMMENT '佣金率',
            `shop_name` VARCHAR(200) COMMENT '店铺名称',
            `shop_id` VARCHAR(64) COMMENT '店铺ID',
            `category_name` VARCHAR(100) COMMENT '分类名称',
            `sell_num` BIGINT COMMENT '销量',
            `platform` VARCHAR(20) COMMENT '平台',
            `raw_data` JSON COMMENT '原始数据（完整JSON）',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_product_id` (`product_id`),
            INDEX `idx_shop_id` (`shop_id`),
            INDEX `idx_category` (`category_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品详情表';
        """
        
        try:
            conn = pymysql.connect(**self.db_config)
            with conn.cursor() as cursor:
                cursor.execute(create_sql)
            conn.commit()
            conn.close()
            self.log.info("商品详情表检查完成")
        except Exception as e:
            self.log.error(f"创建详情表失败: {e}")
    
    def crawl(self, message: Dict[str, Any]) -> Dict:
        """
        爬取商品详情
        
        原理：
        1. 从消息中获取 product_id
        2. 调用 /api/douke/view 接口
        3. 返回详情数据
        
        Args:
            message: 包含 product_id 的消息
            
        Returns:
            商品详情数据
        """
        product_id = message.get('product_id')
        
        if not product_id:
            self.log.error("消息中缺少 product_id")
            return None
        
        self.log.info(f"开始爬取商品详情: {product_id}")
        
        # 短延迟，防止触发风控
        time.sleep(random.uniform(0.1, 0.3))
        
        try:
            # 构造请求参数
            params = {
                'product_id': product_id,
                'platform': 'douyin'
            }
            
            # 获取时间戳和签名
            ts = ReduxSigner.get_timestamp_by_server()
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
            
            # 发送请求
            url = f"{ReduxSigner.BASE_URL}{self.SHOP_VIEW_PATH}"
            response = requests.get(url, params=query_params, headers=headers)
            result = response.json()
            
            # 打印返回结果，方便调试
            self.log.debug(f"接口返回: {result}")
            
            # 判断成功：code=200 或 msg=ok，且有 data
            if result.get('data'):
                self.log.info(f"商品详情获取成功: {product_id}")
                return result['data']
            else:
                self.log.warning(f"商品详情获取失败: {result}")
                return None
                
        except Exception as e:
            self.log.error(f"爬取商品详情失败: {e}")
            return None
    
    def clean(self, data: Dict) -> Dict:
        """
        数据清洗

        清洗规则：
        1. 标题清洗：去空白、截断超长标题
        2. 价格校验：转 float，过滤异常值
        3. 佣金率校验：范围 0-100%
        4. 销量解析：统一 "1000w-2500w" 等格式为数字
        5. 空值填充默认值
        """
        if not data:
            return data

        # 标题清洗
        if data.get('title'):
            data['title'] = data['title'].strip()[:500]

        # 价格字段校验
        for field in ['price', 'coupon', 'coupon_price']:
            val = data.get(field)
            if val is not None:
                try:
                    val = float(val)
                    data[field] = val if 0 <= val <= 999999 else 0
                except (ValueError, TypeError):
                    data[field] = 0

        # 佣金率校验（0-100%）
        for field in ['cos_ratio', 'commission_rate']:
            val = data.get(field)
            if val is not None:
                try:
                    val = float(val)
                    data[field] = val if 0 <= val <= 100 else 0
                except (ValueError, TypeError):
                    data[field] = 0

        # 店铺名清洗
        if data.get('shop_name'):
            data['shop_name'] = data['shop_name'].strip()[:200]

        # 空值填充
        data.setdefault('platform', 'douyin')
        data.setdefault('cover', '')
        data.setdefault('shop_name', '')
        data.setdefault('category_name', '')

        return data
    
    def save(self, data: Dict, message: Dict[str, Any]):
        """
        保存详情数据到数据库
        
        原理：
        1. 提取关键字段
        2. 使用 INSERT ON DUPLICATE KEY UPDATE 实现增量更新
        3. 同时保存原始 JSON 数据，方便后续分析
        
        Args:
            data: 清洗后的详情数据
            message: 原始消息
        """
        if not data:
            self.log.warning("没有数据需要保存")
            return
        
        product_id = message.get('product_id')
        
        # 提取字段（根据实际接口返回调整）
        insert_sql = """
        INSERT INTO `product_detail`
        (product_id, title, cover, price, commission_rate, shop_name, shop_id,
         category_name, sell_num, platform, raw_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            cover = VALUES(cover),
            price = VALUES(price),
            commission_rate = VALUES(commission_rate),
            shop_name = VALUES(shop_name),
            category_name = VALUES(category_name),
            sell_num = VALUES(sell_num),
            raw_data = VALUES(raw_data),
            updated_at = CURRENT_TIMESTAMP
        """

        # 解析销量（API 返回 "1000w-2500w" 这样的字符串）
        sales_raw = data.get('sales', data.get('sell_num', 0))
        sell_num = 0
        if isinstance(sales_raw, (int, float)):
            sell_num = int(sales_raw)
        elif isinstance(sales_raw, str):
            sales_raw = sales_raw.replace(',', '').strip()
            try:
                if 'w' in sales_raw.lower():
                    # 取第一个数字（如 "1000w-2500w" 取 1000）
                    num_str = sales_raw.lower().split('w')[0].split('-')[0]
                    sell_num = int(float(num_str) * 10000)
                elif '万' in sales_raw:
                    num_str = sales_raw.replace('万', '').split('-')[0]
                    sell_num = int(float(num_str) * 10000)
                else:
                    sell_num = int(float(sales_raw.split('-')[0]))
            except (ValueError, IndexError):
                sell_num = 0

        try:
            import json

            conn = pymysql.connect(**self.db_config)
            with conn.cursor() as cursor:
                cursor.execute(insert_sql, (
                    product_id,
                    data.get('title', ''),
                    data.get('cover', ''),
                    data.get('price', 0),
                    data.get('cos_ratio', data.get('commission_rate', 0)),
                    data.get('shop_name', ''),
                    data.get('shop_id', ''),
                    data.get('category_name', ''),
                    sell_num,
                    data.get('platform', 'douyin'),
                    json.dumps(data, ensure_ascii=False)
                ))
            conn.commit()
            conn.close()
            
            self.log.info(f"商品详情保存成功: {product_id}")
            
        except Exception as e:
            self.log.error(f"保存详情失败: {e}")
            raise
    
    def get_next_tasks(self, data: Dict, message: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        生成分析任务

        原理：
        1. 将 product_id 传递到分析队列
        2. 分析接口使用 goods_id（和 product_id 相同）
        3. 即使详情爬取失败也发送，确保分析数据（或 mock）能生成

        Args:
            data: 详情数据
            message: 原始消息

        Returns:
            分析任务列表
        """
        product_id = message.get('product_id')
        task_id = message.get('task_id')
        
        # 生成分析任务
        task = {
            'product_id': product_id,
            'goods_id': product_id,  # 分析接口用 goods_id
            'task_id': task_id
        }
        
        self.log.info(f"生成分析任务: {product_id}")
        return [task]


if __name__ == '__main__':
    """测试 DetailWorker"""
    from crawler.mq.rabbitmq import publish
    from logger import init_logger
    import logging
    
    init_logger(log_dir="logs", log_level=logging.DEBUG)
    
    # 发送测试任务
    test_task = {
        'product_id': '3620889142579355421',
        'task_id': 'test_001'
    }
    
    print("发送测试任务到 detail_q...")
    publish(QUEUE_DETAIL, test_task)
    print("任务已发送，启动 Worker...")
    
    # 启动 Worker
    worker = DetailWorker(
        db_config={
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'Dy@analysis2024',
            'database': 'dy_analysis_system'
        }
    )
    worker.start()
