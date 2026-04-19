# -*- coding: utf-8 -*-
"""
调试 API 返回数据结构
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crawler.dy_xingtui.ReduxSiger import ReduxSigner
import requests

TOKEN = "8d25853f4fde7e460731e890f7284f8f"
BASE_URL = "https://www.reduxingtui.com"

def test_api(api_path, goods_id, start_time, end_time, page_no=1, page_size=10):
    """测试单个 API"""
    params = {
        'goods_id': goods_id,
        'start_time': str(start_time),
        'end_time': str(end_time),
    }
    
    # 分页参数
    if page_no:
        params['page_no'] = str(page_no)
        params['page_size'] = str(page_size)
    
    # 签名
    ts = ReduxSigner.get_timestamp_by_server()
    signer = ReduxSigner.get_siger_by_params(params, ts)
    headers = ReduxSigner.get_headers(signer['header_sign'], signer['timestamp'], TOKEN)
    
    query_params = params.copy()
    query_params['sign'] = signer['url_sign']
    query_params['time'] = signer['timestamp']
    
    url = f"{BASE_URL}/api/douke/dcc{api_path}"
    print(f"\n请求: {url}")
    print(f"参数: {query_params}")
    
    response = requests.get(url, params=query_params, headers=headers)
    result = response.json()
    
    print(f"\n响应 code: {result.get('code')}")
    print(f"响应 msg: {result.get('msg')}")
    
    data = result.get('data')
    print(f"\ndata 类型: {type(data)}")
    
    if isinstance(data, dict):
        print(f"data keys: {list(data.keys())}")
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  {key}: list, 长度={len(value)}")
            elif isinstance(value, dict):
                print(f"  {key}: dict, keys={list(value.keys())[:5]}...")
            else:
                print(f"  {key}: {type(value).__name__} = {value}")
    elif isinstance(data, list):
        print(f"data 是列表，长度: {len(data)}")
        if data:
            print(f"第一个元素 keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")
    
    return data


if __name__ == '__main__':
    from datetime import datetime, timedelta
    
    goods_id = '3620889142579355421'
    now = datetime.now()
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(days=30)).timestamp() * 1000)
    
    print("=" * 60)
    print("测试 goodsUserList (分页接口)")
    print("=" * 60)
    
    data = test_api('/goodsUserList', goods_id, start_time, end_time, page_no=1, page_size=10)
    
    print("\n" + "=" * 60)
    print("测试 goodsLiveList (分页接口)")
    print("=" * 60)
    
    data = test_api('/goodsLiveList', goods_id, start_time, end_time, page_no=1, page_size=10)
    
    print("\n" + "=" * 60)
    print("测试 goodsVideoList (分页接口)")
    print("=" * 60)
    
    data = test_api('/goodsVideoList', goods_id, start_time, end_time, page_no=1, page_size=10)
