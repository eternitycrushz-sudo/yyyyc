# -*- coding: utf-8 -*-
"""
Flask 应用入口

架构说明：
- 使用 Blueprint 拆分路由
- RBAC 权限控制
- JWT 认证
- WebSocket 实时日志推送
"""

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.routes import register_routes
from backend.models.base import init_tables, init_default_data

# 创建 Flask 应用
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = Config.SECRET_KEY

# 跨域配置
CORS(app, resources={r"/api/*": {"origins": "*"}})

# WebSocket
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 注册路由
register_routes(app)


# ============================================
# 前端页面路由
# ============================================

@app.route('/')
@app.route('/home')
def index():
    """首页 - 营销页面"""
    return app.send_static_file('home.html')


@app.route('/login')
def login_redirect():
    """登录页面"""
    return app.send_static_file('login.html')


@app.route('/register')
def register_redirect():
    """注册页面"""
    return app.send_static_file('register.html')


@app.route('/app')
@app.route('/dashboard')
def dashboard():
    """系统后台"""
    return app.send_static_file('index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return app.send_static_file(filename)


# ============================================
# 全局错误处理
# ============================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': '接口不存在'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500


# ============================================
# 健康检查
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'message': 'OK',
        'data': {
            'db_host': Config.DB_HOST,
            'mq_host': Config.MQ_HOST
        }
    })


# ============================================
# WebSocket 事件
# ============================================

@socketio.on('connect')
def handle_connect():
    from flask_socketio import emit
    emit('status', {'status': 'connected'})


# ============================================
# 初始化数据库
# ============================================

def init_app():
    """初始化应用（创建表、默认数据）"""
    try:
        init_tables()
        init_default_data()
        print("应用初始化完成")
    except Exception as e:
        print(f"初始化失败: {e}")


# ============================================
# 启动
# ============================================

if __name__ == '__main__':
    # 初始化数据库表和默认数据
    init_app()
    
    print("\n" + "=" * 50)
    print("Flask 服务启动")
    print("=" * 50)
    print(f"地址: http://localhost:5000")
    print(f"默认账号: admin / admin123")
    print("=" * 50 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True , allow_unsafe_werkzeug=True)
