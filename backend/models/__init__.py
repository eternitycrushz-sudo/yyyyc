# -*- coding: utf-8 -*-
"""
数据模型模块

RBAC 模型说明：
- User（用户）：系统用户
- Role（角色）：如 admin、operator、viewer
- Permission（权限）：如 crawler:start、user:manage
- 关系：User -> Role -> Permission（多对多）
"""

from backend.models.base import get_db_connection, init_tables
from backend.models.user import UserModel
from backend.models.role import RoleModel
from backend.models.permission import PermissionModel

__all__ = [
    'get_db_connection',
    'init_tables',
    'UserModel',
    'RoleModel', 
    'PermissionModel'
]
