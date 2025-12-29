# -*- coding: utf-8 -*-
"""
路由模块

按功能拆分路由，保持代码整洁
"""

from backend.routes.auth import auth_bp
from backend.routes.crawler import crawler_bp
from backend.routes.mq import mq_bp
from backend.routes.user import user_bp


def register_routes(app):
    """注册所有路由蓝图"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(crawler_bp, url_prefix='/api/crawler')
    app.register_blueprint(mq_bp, url_prefix='/api/mq')
    app.register_blueprint(user_bp, url_prefix='/api/user')
