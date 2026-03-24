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
import logging

logger = logging.getLogger(__name__)

try:
    from zhipuai import ZhipuAI
    import httpx
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False
    print("警告: zhipuai 未安装，AI 助手功能不可用")

ai_bp = Blueprint('ai', __name__)

# 初始化智谱 AI 客户端（不使用代理）
if ZHIPU_AVAILABLE:
    # 创建不使用系统代理的 httpx 客户端
    http_client = httpx.Client(
        mounts={
            "https://": httpx.HTTPTransport(proxy=None),
            "http://": httpx.HTTPTransport(proxy=None),
        },
        verify=True,
        timeout=30
    )
    client = ZhipuAI(
        api_key=Config.ZHIPU_API_KEY,
        http_client=http_client
    )


def get_database_context(user_message, product_id=None):
    """
    根据用户消息从数据库获取相关上下文
    如果提供了product_id，则优先提供该商品的详细信息
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    context = []

    # 分类映射（支持更多关键词变体）
    category_mapping = {
        # 美妆个护
        '美妆': '美妆个护',
        '护肤': '美妆个护',
        '彩妆': '美妆个护',
        '口红': '美妆个护',
        '面膜': '美妆个护',

        # 服饰鞋包
        '服饰': '服饰鞋包',
        '鞋': '服饰鞋包',
        '包': '服饰鞋包',
        '衣服': '服饰鞋包',
        '服装': '服饰鞋包',

        # 家居日用
        '家居': '家居日用',
        '日用': '家居日用',
        '家用': '家居日用',
        '清洁': '家居日用',
        '湿巾': '家居日用',

        # 食品饮料（最重要：支持多种说法）
        '食品': '食品饮料',
        '零食': '食品饮料',
        '饮料': '食品饮料',
        '茶': '食品饮料',
        '咖啡': '食品饮料',
        '糖果': '食品饮料',
        '小食': '食品饮料',
        '干果': '食品饮料',

        # 母婴用品
        '母婴': '母婴用品',
        '宝宝': '母婴用品',
        '婴儿': '母婴用品',

        # 数码家电
        '数码': '数码家电',
        '家电': '数码家电',
        '电器': '数码家电',
        '手机': '数码家电',
        '电脑': '数码家电',

        # 运动户外
        '运动': '运动户外',
        '户外': '运动户外',
        '瑜伽': '运动户外',

        # 饰品配件
        '饰品': '饰品配件',
        '配件': '饰品配件',
        '手链': '饰品配件'
    }

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
                    goods_info = f"""当前商品详细信息：
商品名称：{current_goods['title']}
价格：¥{current_goods['price']}
佣金：¥{current_goods['cos_fee']} (佣金率: {current_goods['cos_ratio']}%)
销量：{current_goods['sales']}
浏览量：{current_goods['view_num']}
店铺：{current_goods['shop_name']}

"""
                    context.append(goods_info)
                except Exception as e:
                    logger.error(f"解析商品信息失败: {e}")

        # 检测用户是否在询问特定分类的商品（优先级：精确度高的先匹配）
        specific_category = None
        # 按关键词长度降序排列，确保"零食"优先于"食"匹配
        sorted_keywords = sorted(category_mapping.items(), key=lambda x: len(x[0]), reverse=True)
        for keyword, category in sorted_keywords:
            if keyword in user_message:
                specific_category = category
                logger.info(f"[AI分类] 检测到关键词'{keyword}'，分类为'{specific_category}'")
                break

        # 如果询问特定分类，从本地数据库检索该分类的商品
        if specific_category and any(word in user_message for word in ['有哪些', '商品', '产品', '推荐', '什么', '好的', '买']):
            logger.info(f"[AI分类推荐] 检索'{specific_category}'类商品，用户问题：{user_message}")

            # 构建搜索关键词
            search_keywords = []
            keyword_map = {
                '食品饮料': ['零食', '食品', '饮料', '茶', '咖啡', '糖果', '干果'],
                '美妆个护': ['面膜', '口红', '护肤', '化妆', '美妆', '彩妆'],
                '服饰鞋包': ['衣服', '鞋', '包', '裙', '裤', '服装'],
                '家居日用': ['湿巾', '家居', '清洁', '日用', '毛巾', '垃圾袋'],
                '母婴用品': ['宝宝', '婴儿', '奶瓶', '尿布', '母婴'],
                '数码家电': ['手机', '电脑', '充电', '数码', '家电'],
                '运动户外': ['运动', '瑜伽', '户外', '健身'],
                '饰品配件': ['手链', '项链', '饰品', '配件']
            }

            # 获取该分类的搜索关键词
            if specific_category in keyword_map:
                search_keywords = keyword_map[specific_category]

            # 使用关键词搜索商品
            if search_keywords:
                # 构建WHERE子句：title中包含任意一个关键词
                where_conditions = ' OR '.join([f"title LIKE %s" for _ in search_keywords])
                where_values = [f"%{kw}%" for kw in search_keywords]

                cursor.execute(f"""
                    SELECT product_id, title, price, cos_fee, sales, shop_name, view_num
                    FROM goods_list
                    WHERE ({where_conditions})
                    ORDER BY sales DESC LIMIT 0,20
                """, where_values)

                category_goods = cursor.fetchall()
                logger.info(f"[AI分类推荐] 使用关键词{search_keywords}查询到{len(category_goods)}个商品")
            else:
                category_goods = []
                logger.warning(f"[AI分类推荐] 找不到'{specific_category}'的关键词映射")

            if category_goods and len(category_goods) > 0:
                goods_info = f"\n【{specific_category}商品推荐】\n"
                goods_info += f"从本地数据库检索到的{specific_category}热销商品：\n\n"

                for i, goods in enumerate(category_goods[:12], 1):
                    try:
                        sales_str = str(goods['sales']) if goods['sales'] else '0'
                        # 尝试格式化销量
                        if sales_str.isdigit():
                            sales_display = f"{int(sales_str):,}"
                        else:
                            sales_display = sales_str
                        view_display = f"{goods['view_num']:,}" if isinstance(goods['view_num'], (int, float)) and goods['view_num'] > 0 else str(goods['view_num'])
                    except:
                        sales_display = str(goods['sales'])
                        view_display = str(goods['view_num'])

                    price = float(goods['price']) if goods['price'] else 0
                    cos_fee = float(goods['cos_fee']) if goods['cos_fee'] else 0

                    goods_info += f"【{i}】 {goods['title'][:45]}\n"
                    goods_info += f"   💰 价格:¥{price:.2f}  | 💰 佣金:¥{cos_fee:.2f}\n"
                    goods_info += f"   📊 销量:{sales_display}  | 👁️ 浏览量:{view_display}  | 🏪 店铺:{goods['shop_name']}\n\n"

                context.append(goods_info)
                logger.info(f"[AI分类推荐] ✓ 成功返回{len(category_goods)}个{specific_category}商品")
            else:
                logger.warning(f"[AI分类推荐] 未找到匹配的{specific_category}商品，user_message: {user_message[:100]}")

        # 检测用户是否在询问商品相关信息
        keywords = ['商品', '热门', '推荐', '销量', '价格', '佣金', '类目', '分类', '对比', '分析']
        if any(keyword in user_message for keyword in keywords) and not specific_category:
            # 如果没有当前商品信息且没有特定分类，获取热门商品
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
                    goods_info = "\n当前数据库中的热门商品TOP10（按销量排序）：\n"
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
        if any(word in user_message for word in ['分类', '类目', '类别', '统计']) and not specific_category:
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
            INSERT INTO ai_chat_message (session_id, role, content)
            VALUES (%s, %s, %s)
        """, (session_id, role, content))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"保存聊天记录失败: {e}")


def get_ai_chat_message(user_id, session_id, limit=10):
    """获取聊天历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, created_at
            FROM ai_chat_message
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (session_id, limit))
        
        messages = cursor.fetchall()
        cursor.close()
        conn.close()

        # 反转顺序（从旧到新）
        return [{'role': m['role'], 'content': m['content'], 'created_at': str(m['created_at'])} for m in reversed(messages)]
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
            SELECT session_id FROM ai_chat_session
            WHERE session_id = %s AND user_id = %s
        """, (session_id, user_id))
        
        if not cursor.fetchone():
            # 创建新会话
            cursor.execute("""
                INSERT INTO ai_chat_session (session_id, user_id, title)
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
            print(f"[AI Stream] Starting stream for user {user_id}, message: {user_message[:50]}")

            # 创建或获取会话
            session_id_final = create_or_get_session(user_id, session_id)
            print(f"[AI Stream] Session created/retrieved: {session_id_final}")

            # 保存用户消息
            save_chat_message(user_id, session_id_final, 'user', user_message)
            print(f"[AI Stream] User message saved")

            # 获取数据库上下文
            db_context = get_database_context(user_message, product_id)
            print(f"[AI Stream] Database context retrieved, length: {len(db_context)}")

            # 获取历史对话
            history = get_ai_chat_message(user_id, session_id_final, limit=10)
            print(f"[AI Stream] History retrieved, count: {len(history)}")
            
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
            print(f"[AI Stream] Messages prepared, count: {len(messages)}")

            # 调用智谱 AI 流式接口
            print(f"[AI Stream] Calling ZhipuAI API with glm-4-flash model")
            try:
                response = client.chat.completions.create(
                    model="glm-4-flash",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True  # 启用流式输出
                )
                print(f"[AI Stream] API response received")
            except Exception as api_error:
                print(f"[AI Stream] API Error: {api_error}")
                import traceback
                traceback.print_exc()
                raise
            
            full_reply = ""
            
            # 流式返回数据
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_reply += content

                    # 发送流式数据
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            
            # 保存完整的AI回复
            save_chat_message(user_id, session_id_final, 'assistant', full_reply)
            
            # 发送结束标志
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            print(f"[AI Stream] 错误: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(
        generate_stream(),
        mimetype='text/event-stream',
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

    user_id = g.current_user['user_id']

    try:
        # 创建或获取会话
        session_id = create_or_get_session(user_id, session_id)
        
        # 保存用户消息
        save_chat_message(user_id, session_id, 'user', user_message)
        
        # 获取数据库上下文（传入商品ID）
        db_context = get_database_context(user_message, product_id)
        print(f"[AI Chat] 数据库上下文长度: {len(db_context) if db_context else 0}")
        
        # 获取历史对话
        history = get_ai_chat_message(user_id, session_id, limit=10)
        print(f"[AI Chat] 历史对话数量: {len(history)}")
        
        # 构建消息列表
        system_content = f"""你是抖音电商热点数据分析系统的智能助手。你的职责是：
1. 帮助用户理解和分析电商数据
2. 解答关于商品趋势、销量预测、选品策略的问题
3. 提供数据可视化和报表的使用指导
4. 推荐热门商品和潜力商品

{db_context}

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
        history = get_ai_chat_message(user_id, session_id, limit=50)
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
            FROM ai_chat_session
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


@ai_bp.route('/session/messages', methods=['GET'])
@login_required
def get_session_messages():
    """获取会话历史消息"""
    session_id = (request.args.get('session_id') or '').strip() or 'default'
    limit = int(request.args.get('limit', 50))
    user_id = g.current_user['user_id']

    history = get_ai_chat_message(user_id, session_id, limit=limit)
    return jsonify({
        'success': True,
        'data': history
    })


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


@ai_bp.route('/session/delete', methods=['POST'])
@login_required
def delete_session():
    """删除聊天会话及其所有消息"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    user_id = g.current_user.get('user_id', 1)

    if not session_id:
        return jsonify({
            'success': False,
            'message': '缺少 session_id'
        }), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证会话属于当前用户
        cursor.execute(
            "SELECT id FROM ai_chat_session WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        session = cursor.fetchone()

        if not session:
            return jsonify({
                'success': False,
                'message': '会话不存在或无权访问'
            }), 404

        # 删除该会话的所有消息
        cursor.execute(
            "DELETE FROM ai_chat_message WHERE session_id = %s",
            (session_id,)
        )

        # 删除会话本身
        cursor.execute(
            "DELETE FROM ai_chat_session WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': '会话已删除'
        })
    except Exception as e:
        print(f"删除会话失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500


@ai_bp.route('/history/clear', methods=['POST'])
@login_required
def clear_all_history():
    """清空用户的所有聊天历史"""
    user_id = g.current_user.get('user_id', 1)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取用户的所有session_id
        cursor.execute(
            "SELECT session_id FROM ai_chat_session WHERE user_id = %s",
            (user_id,)
        )
        sessions = cursor.fetchall()

        # 删除所有会话的消息
        for session in sessions:
            cursor.execute(
                "DELETE FROM ai_chat_message WHERE session_id = %s",
                (session['session_id'],)
            )

        # 删除所有会话
        cursor.execute(
            "DELETE FROM ai_chat_session WHERE user_id = %s",
            (user_id,)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': '所有历史记录已清空'
        })
    except Exception as e:
        print(f"清空历史失败: {e}")
        return jsonify({
            'success': False,
            'message': f'清空失败: {str(e)}'
        }), 500
