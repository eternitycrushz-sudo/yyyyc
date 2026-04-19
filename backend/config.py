# -*- coding: utf-8 -*-
"""
Flask 应用配置
"""
import os


class Config:
    """基础配置"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dy-analysis-secret-key-2024')
    
    # JWT 配置
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-key-dy-analysis')
    JWT_EXPIRE_HOURS = int(os.getenv('JWT_EXPIRE_HOURS', 24))
    
    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
    DB_NAME = os.getenv('DB_NAME', 'dy_analysis_system')

    # RabbitMQ 配置
    MQ_HOST = os.getenv('MQ_HOST', 'localhost')
    MQ_PORT = int(os.getenv('MQ_PORT', 5672))
    MQ_USER = os.getenv('MQ_USER', 'guest')
    MQ_PASSWORD = os.getenv('MQ_PASSWORD', 'guest')
    
    # API Token
    API_TOKEN = os.getenv('API_TOKEN', '8d25853f4fde7e460731e890f7284f8f')

    # HTTP 代理配置（用于爬虫请求，防止 IP 被封）
    PROXY_URL = os.getenv('PROXY_URL', '')
    
    # 智谱 AI 配置
    ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY', '92189810e7584172a80f9f85269143bc.pLudIoKZLSY8XoMc')
    
    @classmethod
    def get_db_config(cls):
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME
        }
    
    @classmethod
    def get_mq_config(cls):
        return {
            'host': cls.MQ_HOST,
            'port': cls.MQ_PORT,
            'username': cls.MQ_USER,
            'password': cls.MQ_PASSWORD
        }
