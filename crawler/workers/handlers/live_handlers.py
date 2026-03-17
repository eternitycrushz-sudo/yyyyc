# -*- coding: utf-8 -*-
"""
直播分析相关 Handler

接口：
- goodsLiveSalesTrend: 直播销售趋势（非分页）
- goodsLiveList: 直播列表（分页）
- goodsLiveRelation: 直播关联分析（非分页）
"""

from typing import Dict, Any, List
from crawler.workers.handlers.base_handler import BaseApiHandler


class GoodsLiveTrendHandler(BaseApiHandler):
    """
    直播销售趋势
    
    接口：/api/douke/dcc/goodsLiveSalesTrend
    返回：直播销售趋势数据
    """
    api_name = "直播趋势"
    api_path = "/goodsLiveSalesTrend"
    table_name = "analysis_live_trend_raw"
    is_paged = False
    
    def parse_response(self, data: Any) -> Any:
        if isinstance(data, dict):
            return data.get('trend', data.get('list', [data]))
        return data


class GoodsLiveListHandler(BaseApiHandler):
    """
    直播列表（分页）
    
    接口：/api/douke/dcc/goodsLiveList
    返回：直播场次列表
    
    数据结构：
    {
        "result": [...],
        "total_page": "283",
        "total_record": "2825"
    }
    """
    api_name = "直播列表"
    api_path = "/goodsLiveList"
    table_name = "analysis_live_list_raw"
    is_paged = True
    
    def parse_response(self, data: Any) -> List:
        if isinstance(data, dict):
            return data.get('result', [])
        return data if isinstance(data, list) else []


class GoodsLiveRelationHandler(BaseApiHandler):
    """
    直播关联分析
    
    接口：/api/douke/dcc/goodsLiveRelation
    返回：直播与商品的关联数据
    """
    api_name = "直播关联"
    api_path = "/goodsLiveRelation"
    table_name = "analysis_live_relation_raw"
    is_paged = False
    
    def parse_response(self, data: Any) -> Any:
        if isinstance(data, dict):
            return data.get('relation', data.get('list', data))
        return data
