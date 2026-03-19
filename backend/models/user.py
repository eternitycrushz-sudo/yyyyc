# -*- coding: utf-8 -*-
"""
用户模型
"""
import hashlib
from backend.models.base import get_db_connection


class UserModel:
    """用户数据操作"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码加密"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    @staticmethod
    def find_by_username(username: str) -> dict:
        """根据用户名查找用户"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sys_user WHERE username = %s",
                    (username,)
                )
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def find_by_id(user_id: int) -> dict:
        """根据ID查找用户"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, nickname, email, phone, avatar, status, created_at, password FROM sys_user WHERE id = %s",
                    (user_id,)
                )
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def create(username: str, password: str, nickname: str = None, 
               email: str = None, phone: str = None) -> int:
        """创建用户，返回用户ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO sys_user (username, password, nickname, email, phone)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (username, UserModel.hash_password(password),
                     nickname or username, email, phone)
                )
                last_id = cursor.lastrowid
            conn.commit()
            return last_id
        finally:
            conn.close()
    
    @staticmethod
    def get_user_roles(user_id: int) -> list:
        """获取用户的角色列表"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT r.id, r.code, r.name 
                    FROM sys_role r
                    JOIN sys_user_role ur ON r.id = ur.role_id
                    WHERE ur.user_id = %s AND r.status = 1
                """, (user_id,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_user_permissions(user_id: int) -> list:
        """获取用户的权限列表（通过角色）"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT p.id, p.code, p.name, p.type
                    FROM sys_permission p
                    JOIN sys_role_permission rp ON p.id = rp.permission_id
                    JOIN sys_user_role ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = %s
                """, (user_id,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def has_permission(user_id: int, permission_code: str) -> bool:
        """检查用户是否有某个权限"""
        permissions = UserModel.get_user_permissions(user_id)
        return any(p['code'] == permission_code for p in permissions)
    
    @staticmethod
    def assign_role(user_id: int, role_id: int):
        """给用户分配角色"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT IGNORE INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                    (user_id, role_id)
                )
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def list_users(page: int = 1, size: int = 20) -> dict:
        """分页获取用户列表"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 总数
                cursor.execute("SELECT COUNT(*) as total FROM sys_user")
                total = cursor.fetchone()['total']
                
                # 分页数据
                offset = (page - 1) * size
                cursor.execute("""
                    SELECT id, username, nickname, email, phone, status, created_at 
                    FROM sys_user 
                    ORDER BY id DESC 
                    LIMIT %s OFFSET %s
                """, (size, offset))
                users = cursor.fetchall()
                
                return {
                    'total': total,
                    'page': page,
                    'size': size,
                    'list': users
                }
        finally:
            conn.close()
