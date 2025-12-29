from typing import Dict
import requests
import hashlib
import time
from datetime import datetime, timezone # 引入 timezone 解决时区问题
from pprint import pprint
import pandas as pd
class ReduxSigner:
    """
    ReduxSigner类用于生成Redux的签名。
    """
    cfe = "68ed5a701a0f44de033d6aa276baf3bb" # 密钥
    header_salt = "0ffbc7210302b0313733b862f3bf7e67" #加盐值
    BASE_URL = "https://www.reduxingtui.com"

    @staticmethod
    def _md5(text: str, upper=True) -> str:
        # md5加密函数
        md5 = hashlib.md5()
        md5.update(str(text).encode('utf-8'))
        res = md5.hexdigest()
        return res.upper() if upper else res.lower()

    @staticmethod
    def get_timestamp_by_server():
        # 获取服务器时间戳
        try:
            resp = requests.head(ReduxSigner.BASE_URL, timeout=3)
            server_date = resp.headers.get('date')
            if server_date:
                # 解析 GMT 时间
                # 格式: Fri, 26 Dec 2025 03:41:34 GMT
                dt = datetime.strptime(server_date, '%a, %d %b %Y %H:%M:%S %Z')
                # 修正点1：必须强制设置为 UTC 时区，否则 .timestamp() 会按本地时间计算，导致差8小时
                dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
        except Exception as e:
            print(f"Server time sync failed: {e}, using local time.")
        # 容错处理时间
        return int(time.time())

    @classmethod
    def get_siger_by_params(cls, params: dict, timestamp=None) -> dict:
        if timestamp is None:
            timestamp = cls.get_timestamp_by_server()
        header_sign = cls._md5(f"{timestamp}{cls.header_salt}", upper=False)
        sign_params = params.copy()
        sign_params['time'] = timestamp

        sorted_keys = sorted(sign_params.keys())

        query_parts = []
        for k in sorted_keys:
            query_parts.append(f"{k}={sign_params[k]}")
        query_str = "&".join(query_parts)

        # 拼接 app_secret
        raw_str = f"{query_str}&app_secret={cls.cfe}"

        # 计算 URL 签名
        url_sign = cls._md5(raw_str, upper=True)

        return {
            "header_sign": header_sign,
            "url_sign": url_sign,
            "timestamp": timestamp
        }

    @classmethod
    def get_headers(cls, header_sign: str, timestamp: int, token: str) -> dict:
        """构造完整的请求头"""
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'authori-zation': f'Bearer {token}',
            'form-type': 'pc',
            'sign': header_sign,        # Header 专用签名
            'timestamp': str(timestamp),
            'referer': 'https://www.reduxingtui.com/',
            'cookie': 'think_lang=zh-cn; PHPSESSID=ce151308cca93454c283240fa981d10b', # 建议动态传入
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }

if __name__ == '__main__':
    # 测试
    pass
