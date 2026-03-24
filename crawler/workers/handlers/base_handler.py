# -*- coding: utf-8 -*-
"""
API Handler 基类

原理讲解：
1. 每个分析接口对应一个 Handler
2. Handler 负责：爬取 → 解析 → 保存原始数据
3. 分页接口自动翻页直到没有数据
4. 使用事务保证数据一致性
"""

import time
import random
import json
import requests
import pymysql
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from logger import get_logger


class BaseApiHandler(ABC):
    """
    API 处理器基类
    
    子类需要定义：
    - api_name: 接口名称（用于日志）
    - api_path: 接口路径（如 /goodsTrend）
    - table_name: 原始数据表名（如 analysis_goods_trend_raw）
    - is_paged: 是否是分页接口
    
    子类可以覆盖：
    - parse_response(): 解析响应数据
    - get_extra_params(): 额外的请求参数
    - create_table_sql(): 自定义建表语句
    """
    
    # 子类必须定义
    api_name: str = None
    api_path: str = None
    table_name: str = None
    is_paged: bool = False
    
    # API 配置
    BASE_URL = "https://www.reduxingtui.com"
    BASE_API = "/api/douke/dcc"

    @classmethod
    def _get_token(cls):
        from crawler.token_manager import get_token
        return get_token()
    
    def __init__(self, db_config: Dict, task_manager=None):
        """
        初始化 Handler

        Args:
            db_config: 数据库配置
            task_manager: 任务管理器（可选）
        """
        self.db_config = db_config
        self.task_manager = task_manager
        self.log = get_logger(self.__class__.__name__)

        # 导入签名工具
        from crawler.dy_xingtui.ReduxSiger import ReduxSigner
        self.signer = ReduxSigner

        # 确保表存在
        self._ensure_table()

    def _get_conn(self):
        """获取数据库连接"""
        return pymysql.connect(
            **self.db_config,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _ensure_table(self):
        """确保原始数据表存在"""
        sql = self.create_table_sql()
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()
            conn.close()
        except Exception as e:
            self.log.error(f"创建表失败: {e}")
    
    def create_table_sql(self) -> str:
        """
        创建表的 SQL（子类可覆盖）
        
        默认创建通用结构，存储原始 JSON
        """
        return f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(64) COMMENT '任务ID',
            `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
            `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
            `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
            `page_no` INT DEFAULT 1 COMMENT '页码（分页接口）',
            `raw_data` JSON COMMENT '原始响应数据',
            `data_count` INT DEFAULT 0 COMMENT '数据条数',
            `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_task_id` (`task_id`),
            INDEX `idx_goods_id` (`goods_id`),
            INDEX `idx_is_cleaned` (`is_cleaned`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{self.api_name}原始数据';
        """
    
    def fetch(self, goods_id: str, start_time: int, end_time: int,
              task_id: str = None) -> Dict[str, Any]:
        """
        爬取数据（主入口）
        
        Args:
            goods_id: 商品ID
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）
            task_id: 任务ID
            
        Returns:
            {
                'success': True/False,
                'total_count': 数据总条数,
                'pages': 爬取的页数,
                'raw_ids': 原始数据记录ID列表
            }
        """
        self.log.info(f"开始爬取 {self.api_name}: goods_id={goods_id}")
        
        result = {
            'success': False,
            'total_count': 0,
            'pages': 0,
            'raw_ids': []
        }
        
        try:
            if self.is_paged:
                # 分页接口：循环爬取所有页
                result = self._fetch_all_pages(goods_id, start_time, end_time, task_id)
            else:
                # 非分页接口：只爬一次
                result = self._fetch_single(goods_id, start_time, end_time, task_id)
            
            self.log.info(f"{self.api_name} 爬取完成: {result['total_count']} 条数据")
            
        except Exception as e:
            self.log.error(f"{self.api_name} 爬取失败: {e}")
            result['error'] = str(e)
        
        return result
    
    def _fetch_single(self, goods_id: str, start_time: int, end_time: int,
                      task_id: str = None) -> Dict:
        """爬取单个请求（非分页）"""
        # 构造参数
        params = {
            'goods_id': goods_id,
            'start_time': str(start_time),
            'end_time': str(end_time),
        }
        params.update(self.get_extra_params())
        
        # 发送请求
        data = self._request(params)
        
        if data is None:
            return {'success': False, 'total_count': 0, 'pages': 0, 'raw_ids': []}
        
        # 解析数据
        parsed = self.parse_response(data)
        count = len(parsed) if isinstance(parsed, list) else (1 if parsed else 0)
        
        # 保存原始数据
        raw_id = self._save_raw(
            task_id=task_id,
            goods_id=goods_id,
            start_time=start_time,
            end_time=end_time,
            page_no=1,
            raw_data=data,
            data_count=count
        )
        
        return {
            'success': True,
            'total_count': count,
            'pages': 1,
            'raw_ids': [raw_id]
        }
    
    def _fetch_all_pages(self, goods_id: str, start_time: int, end_time: int,
                         task_id: str = None, page_size: int = 10,
                         max_workers: int = 2) -> Dict:
        """
        爬取所有分页数据（支持多线程）
        
        Args:
            max_workers: 并发线程数，默认2（保守值，避免被封）
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # 先获取第一页，拿到总页数
        self.log.debug(f"{self.api_name} 获取第一页，确定总页数...")
        
        params = {
            'goods_id': goods_id,
            'start_time': str(start_time),
            'end_time': str(end_time),
            'page_no': '1',
            'page_size': str(page_size),
        }
        params.update(self.get_extra_params())
        
        first_data = self._request(params)
        if first_data is None:
            return {'success': False, 'total_count': 0, 'pages': 0, 'raw_ids': []}
        
        # 获取总页数
        total_pages = 1
        total_record = 'N/A'
        if isinstance(first_data, dict):
            total_pages_str = first_data.get('total_page')
            if total_pages_str:
                total_pages = int(total_pages_str)
            total_record = first_data.get('total_record', 'N/A')
        elif isinstance(first_data, list):
            # API 直接返回列表，视为单页数据
            total_pages = 1
            total_record = len(first_data)

        self.log.info(f"{self.api_name} 总页数: {total_pages}, 总记录: {total_record}")
        
        # 保存第一页
        parsed = self.parse_response(first_data)
        count = len(parsed) if isinstance(parsed, list) else 1
        
        raw_id = self._save_raw(
            task_id=task_id,
            goods_id=goods_id,
            start_time=start_time,
            end_time=end_time,
            page_no=1,
            raw_data=first_data,
            data_count=count
        )
        
        total_count = count
        raw_ids = [raw_id]
        
        if total_pages <= 1:
            return {
                'success': True,
                'total_count': total_count,
                'pages': 1,
                'total_pages': total_pages,
                'raw_ids': raw_ids
            }
        
        # 多线程爬取剩余页
        self.log.info(f"{self.api_name} 开始多线程爬取，线程数: {max_workers}")
        
        def fetch_page(page_no):
            """爬取单页"""
            time.sleep(random.uniform(0.2, 0.5))  # 短延迟
            
            params = {
                'goods_id': goods_id,
                'start_time': str(start_time),
                'end_time': str(end_time),
                'page_no': str(page_no),
                'page_size': str(page_size),
            }
            params.update(self.get_extra_params())
            
            data = self._request(params)
            if data is None:
                return page_no, None, 0
            
            parsed = self.parse_response(data)
            count = len(parsed) if isinstance(parsed, list) else 1
            
            return page_no, data, count
        
        # 限制最大页数
        max_page = min(total_pages, 500)
        pages_to_fetch = list(range(2, max_page + 1))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_page, p): p for p in pages_to_fetch}
            
            completed = 0
            for future in as_completed(futures):
                page_no, data, count = future.result()
                completed += 1
                
                if data is not None:
                    # 保存数据
                    raw_id = self._save_raw(
                        task_id=task_id,
                        goods_id=goods_id,
                        start_time=start_time,
                        end_time=end_time,
                        page_no=page_no,
                        raw_data=data,
                        data_count=count
                    )
                    raw_ids.append(raw_id)
                    total_count += count
                
                # 每50页打印一次进度
                if completed % 50 == 0 or completed == len(pages_to_fetch):
                    self.log.info(f"{self.api_name} 进度: {completed}/{len(pages_to_fetch)} 页")
        
        self.log.info(f"{self.api_name} 爬取完成: {total_count} 条数据, {len(raw_ids)} 页")
        
        return {
            'success': True,
            'total_count': total_count,
            'pages': len(raw_ids),
            'total_pages': total_pages,
            'raw_ids': raw_ids
        }
    
    def _get_proxies(self):
        """获取代理配置（禁用代理以解决连接问题）"""
        # 返回空字典强制禁用所有代理，包括系统代理
        return {}

    def _request(self, params: Dict) -> Optional[Dict]:
        """发送 API 请求"""
        from crawler.token_manager import is_token_expired, mark_expired

        try:
            # 获取时间戳和签名
            ts = self.signer.get_timestamp_by_server()
            signer = self.signer.get_siger_by_params(params, ts)

            # 构造请求头
            headers = self.signer.get_headers(
                signer['header_sign'],
                signer['timestamp'],
                self._get_token()
            )

            # 构造 URL 参数
            query_params = params.copy()
            query_params['sign'] = signer['url_sign']
            query_params['time'] = signer['timestamp']

            # 发送请求（禁用代理和SSL验证）
            url = f"{self.BASE_URL}{self.BASE_API}{self.api_path}"
            session = requests.Session()
            session.trust_env = False
            response = session.get(url, params=query_params, headers=headers, timeout=30, proxies={}, verify=False)
            result = response.json()

            # 检查响应
            if result.get('data') is not None:
                return result.get('data')
            else:
                # Token 失效处理：尝试从 token.txt 重新加载并重试
                if not is_token_expired(result):
                    self.log.warning(f"接口返回无数据: {result.get('msg', 'unknown')}")
                    return None

                self.log.warning("检测到 Token 失效，尝试从 token.txt 重新加载...")
                mark_expired()
                new_token = self._get_token()

                # 用新 Token 重试一次
                headers = self.signer.get_headers(
                    signer['header_sign'],
                    signer['timestamp'],
                    new_token
                )
                response2 = session.get(url, params=query_params, headers=headers, timeout=30, proxies={}, verify=False)
                result2 = response2.json()

                if result2.get('data') is not None:
                    self.log.info("Token 重新加载后请求成功")
                    return result2.get('data')
                else:
                    self.log.error(
                        "Token 重新加载后仍然失败。请运行 'python crawler/refresh_token.py' "
                        "手动更新 Token。"
                        f" 接口返回: {result2.get('msg', 'unknown')}"
                    )
                    return None

        except Exception as e:
            self.log.error(f"请求失败: {e}")
            return None
    
    def _save_raw(self, task_id: str, goods_id: str, start_time: int,
                  end_time: int, page_no: int, raw_data: Any,
                  data_count: int) -> int:
        """保存原始数据到数据库"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    INSERT INTO `{self.table_name}`
                    (task_id, goods_id, start_time, end_time, page_no, raw_data, data_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    task_id, goods_id, start_time, end_time, page_no,
                    json.dumps(raw_data, ensure_ascii=False),
                    data_count
                ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_extra_params(self) -> Dict:
        """
        获取额外的请求参数（子类可覆盖）
        """
        return {}
    
    def parse_response(self, data: Any) -> Any:
        """
        解析响应数据（子类可覆盖）
        
        默认直接返回，子类可以提取特定字段
        """
        return data
