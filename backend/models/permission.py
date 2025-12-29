# -*- coding: utf-8 -*-
"""
权限模型
"""
from backend.models.base import get_db_connection


class PermissionModel:
    """权限数据操作"""
    
    @staticmethod
    def find_by_code(code: str) -> dict:
        """根据编码查找权限"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM sys_permission WHERE code = %s", (code,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def list_all() -> list:
        """获取所有权限"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM sys_permission ORDER BY id")
                return cursor.fetchall()
        finally:
            conn.close()
