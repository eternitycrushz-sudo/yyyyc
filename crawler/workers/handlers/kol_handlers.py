# -*- coding: utf-8 -*-
"""
达人分析相关 Handler

接口：
- goodsTrend: 商品趋势（非分页）
- goodsUserTop: 达人TOP排行（非分页）
- goodsUserList: 达人列表（分页）
"""

from typing import Dict, Any, List
from crawler.workers.handlers.base_handler import BaseApiHandler


class GoodsTrendHandler(BaseApiHandler):
    """
    商品趋势分析
    
    接口：/api/douke/dcc/goodsTrend
    返回：趋势数据（销量、销售额等随时间变化）
    """
    api_name = "商品趋势"
    api_path = "/goodsTrend"
    table_name = "analysis_goods_trend_raw"
    is_paged = False
    
    def parse_response(self, data: Any) -> Any:
        """
        解析趋势数据
        
        返回结构通常是：
        {
            "trend": [...],  # 趋势数据
            "summary": {...}  # 汇总数据
        }
        """
        if isinstance(data, dict):
            # 返回趋势列表
            return data.get('trend', data.get('list', [data]))
        return data


class GoodsUserTopHandler(BaseApiHandler):
    """
    达人TOP排行
    
    接口：/api/douke/dcc/goodsUserTop
    返回：销售额/销量TOP的达人列表
    """
    api_name = "达人TOP"
    api_path = "/goodsUserTop"
    table_name = "analysis_user_top_raw"
    is_paged = False
    
    def parse_response(self, data: Any) -> Any:
        """
        解析TOP数据
        
        返回结构通常是列表
        """
        if isinstance(data, dict):
            return data.get('list', data.get('top', []))
        return data if isinstance(data, list) else [data] if data else []


class GoodsUserListHandler(BaseApiHandler):
    """
    达人列表（分页）
    
    接口：/api/douke/dcc/goodsUserList
    返回：带货达人列表，支持分页
    
    数据结构：
    {
        "result": [...],      # 数据列表
        "total_page": "441",  # 总页数
        "total_record": "4407", # 总记录数
        "page_no": "1",
        "page_size": "10"
    }
    """
    api_name = "达人列表"
    api_path = "/goodsUserList"
    table_name = "analysis_user_list_raw"
    is_paged = True  # 分页接口
    
    def parse_response(self, data: Any) -> List:
        """
        解析达人列表
        
        数据在 data['result'] 中
        """
        if isinstance(data, dict):
            return data.get('result', [])
        return data if isinstance(data, list) else []
    
    def create_table_sql(self) -> str:
        """达人列表表结构（可以添加更多索引）"""
        return f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(64) COMMENT '任务ID',
            `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
            `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
            `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
            `page_no` INT DEFAULT 1 COMMENT '页码',
            `raw_data` JSON COMMENT '原始响应数据',
            `data_count` INT DEFAULT 0 COMMENT '数据条数',
            `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_task_id` (`task_id`),
            INDEX `idx_goods_id` (`goods_id`),
            INDEX `idx_page_no` (`page_no`),
            INDEX `idx_is_cleaned` (`is_cleaned`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人列表原始数据';
        """
