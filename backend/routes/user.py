# -*- coding: utf-8 -*-
"""
用户管理路由
"""

from flask import Blueprint, request, jsonify, g
from backend.models.user import UserModel
from backend.models.role import RoleModel
from backend.utils.decorators import login_required, permission_required

user_bp = Blueprint('user', __name__)


@user_bp.route('/list', methods=['GET'])
@login_required
@permission_required('user:list')
def list_users():
    """获取用户列表"""
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 20))
    
    result = UserModel.list_users(page, size)
    
    return jsonify({
        'success': True,
        'data': result
    })


@user_bp.route('/roles', methods=['GET'])
@login_required
def list_roles():
    """获取角色列表"""
    roles = RoleModel.list_all()
    return jsonify({
        'success': True,
        'data': roles
    })


@user_bp.route('/<int:user_id>/assign_role', methods=['POST'])
@login_required
@permission_required('user:update')
def assign_role(user_id):
    """给用户分配角色"""
    data = request.json or {}
    role_id = data.get('role_id')
    
    if not role_id:
        return jsonify({'success': False, 'message': '缺少 role_id'}), 400
    
    try:
        UserModel.assign_role(user_id, role_id)
        return jsonify({
            'success': True,
            'message': '角色分配成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'分配失败: {str(e)}'
        }), 500
