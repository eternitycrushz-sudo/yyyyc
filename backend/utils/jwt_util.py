# -*- coding: utf-8 -*-
"""
JWT 工具

原理：
1. JWT (JSON Web Token) 是一种无状态的认证方式
2. 用户登录后，服务器生成一个 token 返回给前端
3. 前端每次请求都带上这个 token
4. 服务器验证 token 的有效性，不需要查数据库

Token 结构：
- Header: 算法和类型
- Payload: 用户信息（user_id, username, exp 等）
- Signature: 签名，防止篡改
"""

import jwt
import time
from datetime import datetime, timedelta
from backend.config import Config


def create_token(user_id: int, username: str, roles: list = None) -> str:
    """
    创建 JWT Token
    
    Args:
        user_id: 用户ID
        username: 用户名
        roles: 角色列表
        
    Returns:
        JWT token 字符串
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'roles': roles or [],
        'iat': int(time.time()),  # 签发时间
        'exp': int(time.time()) + Config.JWT_EXPIRE_HOURS * 3600  # 过期时间
    }
    
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')


def verify_token(token: str) -> dict:
    """
    验证 JWT Token
    
    Args:
        token: JWT token 字符串
        
    Returns:
        解码后的 payload，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        # Token 已过期
        return None
    except jwt.InvalidTokenError:
        # Token 无效
        return None


def get_token_from_header(headers) -> str:
    """
    从请求头获取 Token
    
    格式：Authorization: Bearer <token>
    """
    auth_header = headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None
