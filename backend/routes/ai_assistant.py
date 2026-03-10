# -*- coding: utf-8 -*-
"""
AI 智能助手路由 - 支持数据库查询和聊天记录
"""

from flask import Blueprint, request, jsonify, stream_with_context, Response, g
from backend.config import Config
from backend.utils.decorators import login_required
from backend.models.base import get_db_connection
import json
import uuid
from datetime import datetime

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


def get_database_context(user_message, product_id=None):
    """
    根据用户消息从数据库获取相关上下文
    如果提供了product_id，则优先提供该商品的详细信息
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    context = []
    
    try:
        # 如果有商品ID，优先获取该商品信息
        if product_id:
            cursor.execute("""
                SELECT title, price, cos_fee, sales, labels, shop_name, view_num, cos_ratio
                FROM goods_list
                WHERE product_id = %s
            """, (product_id,))
            current_goods = cursor.fetchone()
            
            if current_goods:
                try:
                    labels = json.loads(current_goods['labels']) if current_goods['labels'] else []
                    label_names = [l['name'] if isinstance(l, dict) else str(l) for l in labels]
                    
                    goods_info = f"""当前商品详细信息：
商品名称：{current_goods['title']}
价格：¥{current_goods['price']}
佣金：¥{current_goods['cos_fee']} (佣金率: {current_goods['cos_ratio']}%)
销量：{current_goods['sales']}
浏览量：{current_goods['view_num']}
店铺：{current_goods['shop_name']}
分类：{','.join(label_names)}

"""
                    context.append(goods_info)
                    
                    # 获取同类商品推荐
                    if label_names:
                        main_category = label_names[0] if label_names else ''
                        cursor.execute("""
                            SELECT title, price, cos_fee, sales, shop_name
                            FROM goods_list
                            WHERE labels LIKE %s AND product_id != %s
                            ORDER BY sales DESC
                            LIMIT 3
                        """, (f'%{main_category}%', product_id))
                        similar_goods = cursor.fetchall()
                        
                        if similar_goods:
                            similar_info = f"同类商品推荐（{main_category}）：\n"
                            for i, goods in enumerate(similar_goods, 1):
                                similar_info += f"{i}. {goods['title'][:30]}... - 价格:¥{goods['price']}, 佣金:¥{goods['cos_fee']}, 销量:{goods['sales']}\n"
                            context.append(similar_info)
                except Exception as e:
                    print(f"解析商品信息失败: {e}")
        
        # 检测用户是否在询问商品相关信息
        keywords = ['商品', '热门', '推荐', '销量', '价格', '佣金', '类目', '分类', '对比', '分析']
        if any(keyword in user_message for keyword in keywords):
            # 如果没有当前商品信息，获取热门商品
            if not product_id:
                cursor.execute("""
                    SELECT title, price, cos_fee, sales, labels, shop_name
                    FROM goods_list
                    WHERE sales > 0
                    ORDER BY sales DESC
                    LIMIT 10
                """)
                hot_goods = cursor.fetchall()
                
                if hot_goods:
                    goods_info = "当前数据库中的热门商品TOP10（按销量排序）：\n"
                    for i, goods in enumerate(hot_goods, 1):
                        try:
                            labels = json.loads(goods['labels']) if goods['labels'] else []
                            label_names = [l['name'] if isinstance(l, dict) else str(l) for l in labels]
                            sales_display = f"{goods['sales']:,}" if isinstance(goods['sales'], (int, float)) else str(goods['sales'])
                            goods_info += f"{i}. {goods['title'][:40]}...\n   价格:¥{goods['price']}, 佣金:¥{goods['cos_fee']}, 销量:{sales_display}\n   店铺:{goods['shop_name']}, 分类:{','.join(label_names[:2])}\n\n"
                        except Exception as e:
                            goods_info += f"{i}. {goods['title'][:40]}... - 价格:¥{goods['price']}, 佣金:¥{goods['cos_fee']}, 销量:{goods['sales']}\n\n"
                    context.append(goods_info)
        
        # 检测是否询问分类统计
        if any(word in user_message for word in ['分类', '类目', '类别']):
            cursor.execute("""
                SELECT labels
                FROM goods_list
                WHERE labels IS NOT NULL AND labels != ''
                LIMIT 100
            """)
            categories = {}
            for row in cursor.fetchall():
                if row['labels']:
                    try:
                        labels = json.loads(row['labels'])
                        for label in labels:
                            label_name = label['name'] if isinstance(label, dict) else str(label)
                            if label_name in ['饰品配件', '家居日用', '食品饮料', '服饰鞋包', '美妆个护', '数码家电', '母婴用品', '运动户外']:
                                categories[label_name] = categories.get(label_name, 0) + 1
                    except:
                        continue
            
            if categories:
                cat_info = "\n当前商品分类统计：\n"
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    cat_info += f"- {cat}: {count}个商品\n"
                context.append(cat_info)
        
        # 检测是否询问价格区间
        if any(word in user_message for word in ['价格', '便宜', '贵', '多少钱']):
            cursor.execute("""
                SELECT 
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(price) as avg_price
                FROM goods_list
                WHERE price > 0
            """)
            price_stats = cursor.fetchone()
            if price_stats:
                context.append(f"\n价格统计：最低¥{price_stats['min_price']:.2f}, 最高¥{price_stats['max_price']:.2f}, 平均¥{price_stats['avg_price']:.2f}")
        
        # 检测是否询问佣金
        if any(word in user_message for word in ['佣金', '收益', '赚钱']):
            cursor.execute("""
                SELECT title, price, cos_fee, cos_ratio, sales
                FROM goods_list
                WHERE cos_fee > 0
                ORDER BY cos_fee DESC
                LIMIT 5
            """)
            high_commission = cursor.fetchall()
            if high_commission:
                comm_info = "\n高佣金商品TOP5：\n"
                for i, goods in enumerate(high_commission, 1):
                    comm_info += f"{i}. {goods['title'][:30]}... - 佣金:¥{goods['cos_fee']}, 佣金率:{goods['cos_ratio']}%, 销量:{goods['sales']}\n"
                context.append(comm_info)
        
    except Exception as e:
        print(f"获取数据库上下文失败: {e}")
    finally:
        cursor.close()
        conn.close()
    
    return "\n".join(context) if context else ""


def save_chat_message(user_id, session_id, role, content):
    """保存聊天消息到数据库"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_history (user_id, session_id, role, content)
            VALUES (%s, %s, %s, %s)
        """, (user_id, session_id, role, content))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"保存聊天记录失败: {e}")


def get_chat_history(user_id, session_id, limit=10):
    """获取聊天历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, created_at
            FROM chat_history
            WHERE user_id = %s AND session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, session_id, limit))
        
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 反转顺序（从旧到新）
        return [{'role': m['role'], 'content': m['content']} for m in reversed(messages)]
    except Exception as e:
        print(f"获取聊天历史失败: {e}")
        return []


def create_or_get_session(user_id, session_id=None):
    """创建或获取会话"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 检查会话是否存在
        cursor.execute("""
            SELECT session_id FROM chat_sessions
            WHERE session_id = %s AND user_id = %s
        """, (session_id, user_id))
        
        if not cursor.fetchone():
            # 创建新会话
            cursor.execute("""
                INSERT INTO chat_sessions (session_id, user_id, title)
                VALUES (%s, %s, %s)
            """, (session_id, user_id, '新对话'))
            conn.commit()
        
        cursor.close()
        conn.close()
        return session_id
    except Exception as e:
        print(f"创建会话失败: {e}")
        return session_id or str(uuid.uuid4())


@ai_bp.route('/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    """
    AI 助手流式对话接口
    """
    if not ZHIPU_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 助手功能未启用，请安装 zhipuai: pip install zhipuai'
        }), 503
    
    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', '')
    product_id = data.get('product_id', '')
    user_id = g.current_user.get('user_id', 1)
    
    if not user_message:
        return jsonify({
            'success': False,
            'message': '消息不能为空'
        }), 400
    
    def generate_stream():
        try:
            # 创建或获取会话
            session_id_final = create_or_get_session(user_id, session_id)
            
            # 保存用户消息
            save_chat_message(user_id, session_id_final, 'user', user_message)
            
            # 获取数据库上下文
            db_context = get_database_context(user_message, product_id)
            
            # 获取历史对话
            history = get_chat_history(user_id, session_id_final, limit=10)
            
            # 构建消息列表
            system_content = f"""你是抖音电商热点数据分析系统的智能助手。你的职责是：
1. 帮助用户理解和分析电商数据
2. 解答关于商品趋势、销量预测、选品策略的问题
3. 提供数据可视化和报表的使用指导
4. 推荐热门商品和潜力商品

{db_context if db_context else ''}

请用专业、友好的语气回答用户问题，并尽可能提供具体的数据分析建议。如果有数据库中的商品信息，请优先推荐这些商品。"""

            if product_id:
                system_content += f"\n\n当前用户正在查看商品ID为 {product_id} 的商品详情页面，请优先基于这个商品提供分析和建议。"
            
            messages = [{"role": "system", "content": system_content}]
            
            # 添加历史对话
            if history:
                messages.extend(history[:-1])
            
            messages.append({"role": "user", "content": user_message})
            
            # 调用智谱 AI 流式接口
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True  # 启用流式输出
            )
            
            full_reply = ""
            
            # 流式返回数据
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_reply += content
                    
                    # 发送流式数据
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            # 保存完整的AI回复
            save_chat_message(user_id, session_id_final, 'assistant', full_reply)
            
            # 发送结束标志
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            print(f"[AI Stream] 错误: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        generate_stream(),
        mimetype='text/plain',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    )

@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    AI 助手对话接口（支持数据库查询）
    """
    if not ZHIPU_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 助手功能未启用，请安装 zhipuai: pip install zhipuai'
        }), 503
    
    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', '')
    product_id = data.get('product_id', '')  # 新增：商品ID参数
    user_id = g.current_user.get('user_id', 1)
    
    # 添加调试日志
    print(f"[AI Chat] 用户ID: {user_id}, 消息: {user_message[:50]}..., 商品ID: {product_id}")
    print(f"[AI Chat] 当前用户信息: {g.current_user}")
    
    if not user_message:
        return jsonify({
            'success': False,
            'message': '消息不能为空'
        }), 400
    
    try:
        # 创建或获取会话
        session_id = create_or_get_session(user_id, session_id)
        
        # 保存用户消息
        save_chat_message(user_id, session_id, 'user', user_message)
        
        # 获取数据库上下文（传入商品ID）
        db_context = get_database_context(user_message, product_id)
        print(f"[AI Chat] 数据库上下文长度: {len(db_context) if db_context else 0}")
        
        # 获取历史对话
        history = get_chat_history(user_id, session_id, limit=10)
        print(f"[AI Chat] 历史对话数量: {len(history)}")
        
        # 构建消息列表
        system_content = f"""你是抖音电商热点数据分析系统的智能助手。你的职责是：
1. 帮助用户理解和分析电商数据
2. 解答关于商品趋势、销量预测、选品策略的问题
3. 提供数据可视化和报表的使用指导
4. 推荐热门商品和潜力商品

{db_context if db_context else ''}

请用专业、友好的语气回答用户问题，并尽可能提供具体的数据分析建议。如果有数据库中的商品信息，请优先推荐这些商品。"""

        # 如果有商品ID，调整系统提示
        if product_id:
            system_content += f"\n\n当前用户正在查看商品ID为 {product_id} 的商品详情页面，请优先基于这个商品提供分析和建议。"
        
        messages = [
            {
                "role": "system",
                "content": system_content
            }
        ]
        
        # 添加历史对话（排除当前消息）
        if history:
            messages.extend(history[:-1])
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        print(f"[AI Chat] 发送给AI的消息数量: {len(messages)}")
        
        # 调用智谱 AI
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        # 提取回复
        reply = response.choices[0].message.content
        print(f"[AI Chat] AI回复长度: {len(reply)}")
        
        # 保存AI回复
        save_chat_message(user_id, session_id, 'assistant', reply)
        
        return jsonify({
            'success': True,
            'data': {
                'reply': reply,
                'session_id': session_id,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        })
        
    except Exception as e:
        print(f"[AI Chat] 错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'AI 调用失败: {str(e)}'
        }), 500


@ai_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """获取用户的聊天历史"""
    session_id = request.args.get('session_id', '')
    user_id = g.current_user.get('user_id', 1)
    
    if not session_id:
        return jsonify({
            'success': False,
            'message': '缺少session_id'
        }), 400
    
    try:
        history = get_chat_history(user_id, session_id, limit=50)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取历史失败: {str(e)}'
        }), 500


@ai_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """获取用户的所有会话"""
    user_id = g.current_user.get('user_id', 1)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, title, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT 20
        """, (user_id,))
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取会话列表失败: {str(e)}'
        }), 500


@ai_bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """获取 AI 助手的快捷问题建议"""
    suggestions = [
        "推荐几个当前热门的商品",
        "哪些商品佣金最高？",
        "美妆类目有哪些商品？",
        "价格在50-100元的商品有哪些？",
        "帮我分析一下商品销量趋势",
        "如何提高商品转化率？"
    ]
    
    return jsonify({
        'success': True,
        'data': suggestions
    })
