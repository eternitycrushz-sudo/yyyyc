# -*- coding: utf-8 -*-
"""
路由模块

按功能拆分路由，保持代码整洁
"""

from backend.routes.auth import auth_bp
from backend.routes.crawler import crawler_bp
from backend.routes.mq import mq_bp
from backend.routes.user import user_bp
from backend.routes.goods import goods_bp
from backend.routes.goods_analysis import goods_analysis_bp
from backend.routes.ai_assistant import ai_bp
from backend.routes.export import export_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.scheduler import scheduler_bp
from backend.routes.prediction import prediction_bp
from backend.routes.oplog import oplog_bp
from backend.routes.favorites import favorites_bp
from backend.routes.notification import notification_bp
from backend.routes.compare import compare_bp
from backend.routes.report import report_bp
from backend.routes.settings import settings_bp


def register_routes(app):
    """注册所有路由蓝图"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(crawler_bp, url_prefix='/api/crawler')
    app.register_blueprint(mq_bp, url_prefix='/api/mq')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(goods_bp, url_prefix='/api/goods')
    app.register_blueprint(goods_analysis_bp, url_prefix='/api/goods/analysis')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(scheduler_bp, url_prefix='/api/scheduler')
    app.register_blueprint(prediction_bp, url_prefix='/api/prediction')
    app.register_blueprint(oplog_bp, url_prefix='/api/oplog')
    app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
    app.register_blueprint(notification_bp, url_prefix='/api/notification')
    app.register_blueprint(compare_bp, url_prefix='/api/compare')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
