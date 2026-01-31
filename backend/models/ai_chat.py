# -*- coding: utf-8 -*-
"""
AI 会话与消息模型
"""
from backend.models.base import get_db_connection


class AiChatModel:
    @staticmethod
    def get_session(user_id, session_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, user_id, session_id, title, created_at, updated_at FROM ai_chat_session WHERE user_id = %s AND session_id = %s",
                    (user_id, session_id)
                )
                return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def ensure_session(user_id, session_id, title=None):
        existing = AiChatModel.get_session(user_id, session_id)
        if existing:
            return existing['id'], False

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ai_chat_session (user_id, session_id, title) VALUES (%s, %s, %s)",
                    (user_id, session_id, title)
                )
                conn.commit()
                return cursor.lastrowid, True
        finally:
            conn.close()

    @staticmethod
    def update_session_title(session_pk, title):
        if not title:
            return
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE ai_chat_session SET title = %s WHERE id = %s AND (title IS NULL OR title = '')",
                    (title, session_pk)
                )
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def add_message(session_pk, role, content):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ai_chat_message (session_id, role, content) VALUES (%s, %s, %s)",
                    (session_pk, role, content)
                )
                cursor.execute(
                    "UPDATE ai_chat_session SET updated_at = NOW() WHERE id = %s",
                    (session_pk,)
                )
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_recent_messages(session_pk, limit=10):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT role, content, created_at FROM ai_chat_message WHERE session_id = %s ORDER BY id DESC LIMIT %s",
                    (session_pk, limit)
                )
                rows = cursor.fetchall() or []
                rows.reverse()
                return rows
        finally:
            conn.close()

    @staticmethod
    def list_sessions(user_id, limit=50):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT session_id, title, created_at, updated_at FROM ai_chat_session WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
                    (user_id, limit)
                )
                return cursor.fetchall() or []
        finally:
            conn.close()
