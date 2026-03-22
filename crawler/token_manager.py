# -*- coding: utf-8 -*-
"""
Token 管理模块

职责：
1. 统一管理 API_TOKEN 读取
2. 监控 token.txt 文件变化（mtime），实现热更新
3. 检测 Token 失效并标记
4. 线程安全（与 SessionManager 同模式）

优先级：token.txt > config.py > 硬编码兜底
"""

import os
import threading
import logging

# token.txt 放在项目根目录，与 config.py 同级
_TOKEN_FILE = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
    "token.txt"
)
_FALLBACK_TOKEN = "7036afebb8e8c2449c74718738fa33bb"
_EXPIRED_MSG = "登录状态有误"

# 全局缓存（线程安全）
_lock = threading.Lock()
_cached_token = None
_cache_mtime = 0.0        # token.txt 上次读取时的 mtime


def get_token() -> str:
    """
    读取当前有效 Token。

    优先级：
    1. token.txt（如果文件存在且格式正确）
    2. config.py 中的 API_TOKEN（进程内静态值）
    3. 硬编码兜底值

    使用文件 mtime 实现热更新：
    - 当 token.txt 被修改（mtime 变化）时，自动重新加载
    - 否则使用缓存，避免高频 I/O
    """
    global _cached_token, _cache_mtime

    with _lock:
        try:
            mtime = os.path.getmtime(_TOKEN_FILE)
        except FileNotFoundError:
            mtime = 0.0

        # 文件 mtime 变化 → 文件被外部更新（token.txt 或 mark_expired 后重读）
        if mtime != _cache_mtime or _cached_token is None:
            _cached_token = _read_token_file() or _get_config_token() or _FALLBACK_TOKEN
            _cache_mtime = mtime

        return _cached_token


def mark_expired():
    """
    标记当前 Token 已失效（通常由 _request() 在检测到"登录状态有误"时调用）。

    做法：将 _cache_mtime 置为 0，强制下次 get_token() 重新读取文件。
    这样如果 token.txt 已被更新（比如 refresh_token.py 写入），
    立即生效；如果文件未更新，回退 config.py。
    """
    global _cache_mtime
    with _lock:
        _cache_mtime = 0.0


def is_token_expired(result: dict) -> bool:
    """
    判断 API 响应是否为 Token 失效错误。

    Args:
        result: 服务器返回的 JSON 对象

    Returns:
        True 表示检测到 Token 失效，False 表示其他错误或成功
    """
    msg = result.get('msg', '')
    return _EXPIRED_MSG in str(msg)


def write_token_file(token: str):
    """
    将新 Token 写入 token.txt（由 refresh_token.py 调用）。

    写入后自动调用 mark_expired()，使缓存失效，
    下次 get_token() 立即读取新文件内容。

    Args:
        token: 新的 API Token（32 位 hex 字符串）
    """
    token = token.strip()
    with open(_TOKEN_FILE, 'w', encoding='utf-8') as f:
        f.write(token)

    mark_expired()  # 清除缓存，强制下次 get_token() 重读文件

    logger = logging.getLogger("TokenManager")
    logger.info(f"Token 已写入 token.txt: {_TOKEN_FILE}")


def _read_token_file() -> str:
    """
    从 token.txt 读取 Token（内部函数）。

    验证格式：必须是 32 位小写十六进制字符串。
    不合法的格式会被忽略（返回空字符串）。
    """
    try:
        with open(_TOKEN_FILE, 'r', encoding='utf-8') as f:
            token = f.read().strip()

        # 验证格式：32 位 hex 字符串
        if len(token) == 32 and all(c in '0123456789abcdef' for c in token):
            return token
        else:
            logger = logging.getLogger("TokenManager")
            logger.warning(
                f"token.txt 内容格式不合法（期望 32 位十六进制，获得 {len(token)} 个字符）"
            )
            return ''
    except FileNotFoundError:
        # token.txt 不存在，回退到 config.py
        return ''
    except Exception as e:
        logger = logging.getLogger("TokenManager")
        logger.warning(f"读取 token.txt 失败: {e}")
        return ''


def _get_config_token() -> str:
    """
    从 config.py 读取 API_TOKEN（内部函数）。
    作为对 token.txt 的回退方案。
    """
    try:
        from config import get_config
        return get_config().API_TOKEN
    except Exception:
        return ''
