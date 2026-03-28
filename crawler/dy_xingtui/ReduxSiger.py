from typing import Dict
import requests
import hashlib
import time
import threading
from datetime import datetime, timezone
from pprint import pprint
import pandas as pd
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_proxies():
    """获取代理配置（禁用代理以解决连接问题）"""
    # 返回空字典强制禁用所有代理，包括系统代理
    return {}


class SessionManager:
    """
    动态管理 PHPSESSID，自动获取和刷新。

    原理：
    1. 首次请求时访问 reduxingtui.com 获取 Set-Cookie 中的 PHPSESSID
    2. 缓存 session_id，过期后自动刷新
    3. 线程安全
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._session_id = None
        self._last_refresh = 0
        self._ttl = 1200  # 20 分钟刷新一次（PHP 默认 session 超时 24 分钟）

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_session_id(self) -> str:
        """获取有效的 PHPSESSID，过期则自动刷新"""
        now = time.time()
        if self._session_id and (now - self._last_refresh) < self._ttl:
            return self._session_id

        with self._lock:
            # 双重检查
            if self._session_id and (time.time() - self._last_refresh) < self._ttl:
                return self._session_id
            return self._refresh()

    def _refresh(self) -> str:
        """访问网站首页获取新的 PHPSESSID"""
        try:
            proxies = _get_proxies()
            # 创建Session禁用代理
            session = requests.Session()
            session.trust_env = False
            resp = session.get(
                "https://www.reduxingtui.com/",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/143.0.0.0 Safari/537.36'
                },
                timeout=10,
                allow_redirects=True,
                proxies={},
                verify=False
            )
            cookies = resp.cookies.get_dict()
            session_id = cookies.get('PHPSESSID')
            if session_id:
                self._session_id = session_id
                self._last_refresh = time.time()
                return self._session_id

            # 从 Set-Cookie header 中解析
            set_cookie = resp.headers.get('Set-Cookie', '')
            for part in set_cookie.split(';'):
                part = part.strip()
                if part.startswith('PHPSESSID='):
                    self._session_id = part.split('=', 1)[1]
                    self._last_refresh = time.time()
                    return self._session_id

        except Exception as e:
            print(f"[SessionManager] 获取 PHPSESSID 失败: {e}")

        # 如果获取失败且有旧值，继续使用旧值
        if self._session_id:
            return self._session_id

        # 兜底：使用有效的登录 Session ID
        self._session_id = '590b8176be814a074bf6eaf719411915'
        self._last_refresh = time.time()
        return self._session_id

    def invalidate(self):
        """手动标记 session 失效，强制下次刷新"""
        self._last_refresh = 0


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

    # 时间戳缓存：避免每次请求都去获取服务器时间
    _ts_cache = {'server_ts': 0, 'local_ts': 0}
    _ts_lock = threading.Lock()

    @staticmethod
    def get_timestamp_by_server():
        """获取服务器时间戳（缓存30秒，避免每次都发HTTP请求）"""
        now = time.time()
        cache = ReduxSigner._ts_cache

        # 30秒内使用缓存：用本地时间差推算服务器时间
        if cache['server_ts'] and (now - cache['local_ts']) < 30:
            return int(cache['server_ts'] + (now - cache['local_ts']))

        with ReduxSigner._ts_lock:
            # 双重检查
            if cache['server_ts'] and (now - cache['local_ts']) < 30:
                return int(cache['server_ts'] + (now - cache['local_ts']))

            try:
                session = requests.Session()
                session.trust_env = False
                resp = session.head(ReduxSigner.BASE_URL, timeout=10, proxies={}, verify=False)
                server_date = resp.headers.get('date')
                if server_date:
                    dt = datetime.strptime(server_date, '%a, %d %b %Y %H:%M:%S %Z')
                    dt = dt.replace(tzinfo=timezone.utc)
                    server_ts = int(dt.timestamp())
                    cache['server_ts'] = server_ts
                    cache['local_ts'] = now
                    return server_ts
            except Exception as e:
                print(f"Server time sync failed: {e}, using local time.")

            return int(now)

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
        """构造完整的请求头，PHPSESSID 自动动态获取"""
        session_id = SessionManager.get_instance().get_session_id()
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'authorization': f'Bearer {token}',
            'form-type': 'pc',
            'sign': header_sign,
            'timestamp': str(timestamp),
            'referer': 'https://www.reduxingtui.com/',
            'cookie': f'think_lang=zh-cn; PHPSESSID={session_id}; Hm_lvt_501b09fd10148a079718b7e46ad9e514=1773933823,1773969543; Hm_lpvt_501b09fd10148a079718b7e46ad9e514=1773969543; HMACCOUNT=D3585355A99BC857',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }

if __name__ == '__main__':
    # 测试
    pass
