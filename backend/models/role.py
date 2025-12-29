# -*- coding: utf-8 -*-
"""
角色模型
"""
from backend.models.base import get_db_connection


class RoleModel:
    """角色数据操作"""
    
    @staticmethod
    def find_by_code(code: str) -> dict:
        """根据编码查找角色"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM sys_role WHERE code = %s", (code,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def find_by_id(role_id: int) -> dict:
        """根据ID查找角色"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM sys_role WHERE id = %s", (role_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def list_all() -> list:
        """获取所有角色"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM sys_role WHERE status = 1 ORDER BY id")
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_role_permissions(role_id: int) -> list:
        """获取角色的权限列表"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.code, p.name, p.type
                    FROM sys_permission p
                    JOIN sys_role_permission rp ON p.id = rp.permission_id
                    WHERE rp.role_id = %s
                """, (role_id,))
                return cursor.fetchall()
        finally:
            conn.close()
