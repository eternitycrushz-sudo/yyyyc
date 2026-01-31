# -*- coding: utf-8 -*-
"""
AI 智能助手路由
"""

from flask import Blueprint, request, jsonify, stream_with_context, Response, g
from backend.config import Config
from backend.utils.decorators import login_required
from backend.models.ai_chat import AiChatModel
import json

try:
    from zhipuai import ZhipuAI
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False
    print("警告: zhipuai 未安装，AI 助手功能不可用")

ai_bp = Blueprint('ai', __name__)

# 初始化智谱 AI 客户端
if ZHIPU_AVAILABLE:
    client = ZhipuAI(api_key=Config.ZHIPU_API_KEY)


SYSTEM_PROMPT = (
    "你是抖音电商热点数据分析系统的智能助手。你的职责是：\n"
    "1. 帮助用户理解和分析电商数据\n"
    "2. 解答关于商品趋势、销量预测、选品策略的问题\n"
    "3. 提供数据可视化和报表的使用指导\n"
    "4. 推荐热门商品和潜力商品\n\n"
    "请用专业、友好的语气回复用户问题，并尽可能提供具体的数据分析建议。"
)


def _get_session_id(data):
    session_id = (data.get('session_id') or '').strip()
    return session_id if session_id else 'default'


@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    AI 助手对话接口

    请求：
    {
        "message": "用户消息",
        "history": [
            {"role": "user", "content": "历史消息1"},
            {"role": "assistant", "content": "AI回复1"}
        ],
        "session_id": "xxxx"
    }

    响应：
    {
        "success": true,
        "data": {
            "reply": "AI 回复内容"
        }
    }
    """
    if not ZHIPU_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 助手功能未启用，请安装 zhipuai: pip install zhipuai'
        }), 503

    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = _get_session_id(data)

    if not user_message:
        return jsonify({
            'success': False,
            'message': '消息不能为空'
        }), 400

    user_id = g.current_user['user_id']
    session_pk, created = AiChatModel.ensure_session(user_id, session_id)
    if created:
        AiChatModel.update_session_title(session_pk, user_message[:50])

    try:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        history = AiChatModel.get_recent_messages(session_pk, limit=10)
        if history:
            messages.extend([{"role": m['role'], "content": m['content']} for m in history])

        messages.append({
            "role": "user",
            "content": user_message
        })

        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        reply = response.choices[0].message.content

        AiChatModel.add_message(session_pk, "user", user_message)
        AiChatModel.add_message(session_pk, "assistant", reply)

        return jsonify({
            'success': True,
            'data': {
                'reply': reply,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI 调用失败: {str(e)}'
        }), 500


@ai_bp.route('/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    """
    AI 助手流式对话接口（支持打字机效果）
    """
    if not ZHIPU_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 助手功能未启用'
        }), 503

    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = _get_session_id(data)

    if not user_message:
        return jsonify({
            'success': False,
            'message': '消息不能为空'
        }), 400

    user_id = g.current_user['user_id']
    session_pk, created = AiChatModel.ensure_session(user_id, session_id)
    if created:
        AiChatModel.update_session_title(session_pk, user_message[:50])

    def generate():
        assistant_chunks = []
        try:
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                }
            ]

            history = AiChatModel.get_recent_messages(session_pk, limit=10)
            if history:
                messages.extend([{"role": m['role'], "content": m['content']} for m in history])

            messages.append({
                "role": "user",
                "content": user_message
            })

            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_chunks.append(content)
                    yield f"data: {json.dumps({'content': content})}\n\n"

            assistant_text = ''.join(assistant_chunks).strip()
            AiChatModel.add_message(session_pk, "user", user_message)
            if assistant_text:
                AiChatModel.add_message(session_pk, "assistant", assistant_text)

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@ai_bp.route('/session/messages', methods=['GET'])
@login_required
def get_session_messages():
    """
    获取会话历史消息
    参数:
        session_id: 会话ID
        limit: 最大消息数
    """
    session_id = (request.args.get('session_id') or '').strip() or 'default'
    limit = int(request.args.get('limit', 50))
    if limit < 1:
        limit = 50
    if limit > 200:
        limit = 200

    user_id = g.current_user['user_id']
    session = AiChatModel.get_session(user_id, session_id)
    if not session:
        return jsonify({
            'success': True,
            'data': []
        })

    messages = AiChatModel.get_recent_messages(session['id'], limit=limit)
    return jsonify({
        'success': True,
        'data': messages
    })


@ai_bp.route('/sessions', methods=['GET'])
@login_required
def list_sessions():
    """
    获取会话列表
    参数:
        limit: 最大会话数
    """
    limit = int(request.args.get('limit', 50))
    if limit < 1:
        limit = 50
    if limit > 200:
        limit = 200

    user_id = g.current_user['user_id']
    sessions = AiChatModel.list_sessions(user_id, limit=limit)
    return jsonify({
        'success': True,
        'data': sessions
    })


@ai_bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """
    获取 AI 助手的快捷问题建议
    """
    suggestions = [
        "帮我分析一下最近的热门商品趋势",
        "推荐几个高潜力的商品类目",
        "如何提高商品的转化率？",
        "美妆类目的销量预测如何？",
        "哪些商品适合在双十一推广？",
        "如何使用数据分析功能？"
    ]

    return jsonify({
        'success': True,
        'data': suggestions
    })
