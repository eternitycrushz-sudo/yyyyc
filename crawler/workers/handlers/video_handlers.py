# -*- coding: utf-8 -*-
"""
视频分析相关 Handler

接口：
- goodsVideosales: 视频销售分析（非分页）
- goodsVideoList: 视频列表（分页）
- goodsVideoTime: 视频时间分析（非分页）
"""

from typing import Dict, Any, List
from crawler.workers.handlers.base_handler import BaseApiHandler


class GoodsVideoSalesHandler(BaseApiHandler):
    """
    视频销售分析
    
    接口：/api/douke/dcc/goodsVideosales
    返回：视频带货销售数据
    """
    api_name = "视频销售"
    api_path = "/goodsVideosales"
    table_name = "analysis_video_sales_raw"
    is_paged = False
    
    def parse_response(self, data: Any) -> Any:
        if isinstance(data, dict):
            return data.get('sales', data.get('list', data))
        return data


class GoodsVideoListHandler(BaseApiHandler):
    """
    视频列表（分页）
    
    接口：/api/douke/dcc/goodsVideoList
    返回：带货视频列表
    
    数据结构：
    {
        "result": [...],
        "total_page": "607",
        "total_record": "6061"
    }
    """
    api_name = "视频列表"
    api_path = "/goodsVideoList"
    table_name = "analysis_video_list_raw"
    is_paged = True
    
    def parse_response(self, data: Any) -> List:
        if isinstance(data, dict):
            return data.get('result', [])
        return data if isinstance(data, list) else []


class GoodsVideoTimeHandler(BaseApiHandler):
    """
    视频时间分析
    
    接口：/api/douke/dcc/goodsVideoTime
    返回：视频发布时间分布分析
    """
    api_name = "视频时间"
    api_path = "/goodsVideoTime"
    table_name = "analysis_video_time_raw"
    is_paged = False
    
    def parse_response(self, data: Any) -> Any:
        if isinstance(data, dict):
            return data.get('time_dist', data.get('list', data))
        return data
