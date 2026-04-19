# DY Analysis System — 抖音电商数据分析与热点预测平台

> 一个面向抖音小店运营者、电商数据分析师和品牌方的全栈数据分析 SaaS 平台，涵盖分布式爬虫、数据清洗、热点预测、AI 智能助手与 Web 可视化。

---

## 目录

- [项目概览](#项目概览)
- [整体架构](#整体架构)
- [技术栈](#技术栈)
- [功能模块详解](#功能模块详解)
  - [身份认证与权限管理](#身份认证与权限管理)
  - [分布式爬虫系统](#分布式爬虫系统)
  - [数据清洗管道](#数据清洗管道)
  - [商品数据接口](#商品数据接口)
  - [热点预测引擎](#热点预测引擎)
  - [AI 智能助手](#ai-智能助手)
  - [数据仪表盘](#数据仪表盘)
  - [数据导出](#数据导出)
  - [系统设置与用户管理](#系统设置与用户管理)
- [数据库设计](#数据库设计)
- [如何运行](#如何运行)
- [API 参考](#api-参考)
- [日志与监控](#日志与监控)
- [安全设计](#安全设计)

---

## 项目概览

**DY Analysis System** 是一个面向抖音电商（Douyin 小店）场景的数据分析与决策支持平台。系统从抖音官方 API 自动采集商品、直播、视频、达人等多维度数据，经过清洗、分析后在 Web 端以图表、大屏、词云等形式呈现，并集成了基于智谱 GLM-4 的 AI 助手，支持自然语言查询数据库。

**适用角色**：

- 抖音小店运营者：追踪竞品动态、发现热销品类
- 电商数据分析师：构建数据看板、导出报表
- 品牌方/投放方：预测热点商品、优化投放策略

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web 前端 (Vanilla JS)                   │
│  login / dashboard / crawler / prediction / ai_assistant     │
│  bigscreen / products / goods_detail / compare / settings    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                   Flask 后端 (port 5001)                     │
│  Blueprint: auth / goods / crawler / prediction / ai /       │
│             dashboard / export / report / settings / mq      │
│  中间件: JWT 认证 · RBAC 权限 · CORS · SocketIO 实时推送     │
└───────────┬──────────────────────────┬──────────────────────┘
            │                          │
┌───────────▼───────┐      ┌───────────▼───────────────────┐
│   MySQL 8.0       │      │       RabbitMQ                 │
│  (业务数据存储)    │      │  list_q / detail_q /           │
│  (用户权限系统)    │      │  analysis_q / dead_letter      │
└───────────────────┘      └───────────┬───────────────────┘
                                       │ AMQP
┌──────────────────────────────────────▼──────────────────────┐
│                     Worker 进程集群                          │
│  ListWorker → DetailWorker → AnalysisWorker → CleanWorker   │
│                    ↓                                         │
│           Douyin API (with Redux 签名)                       │
└─────────────────────────────────────────────────────────────┘
```

**数据流**：

```
用户提交任务
    → list_q
        → ListWorker (爬商品列表)
            → detail_q
                → DetailWorker (爬商品详情)
                    → analysis_q
                        → AnalysisWorker (爬趋势/直播/视频/达人)
                            → CleanWorker (验证·去重·转换)
                                → MySQL (清洗后数据)
```

---

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask 2.3+ | 轻量微框架，Blueprint 模块化路由 |
| 实时通信 | Flask-SocketIO 5.3+ | WebSocket 推送爬虫日志 |
| 认证 | PyJWT 2.8+ | JWT HS256，24 小时有效期 |
| 数据库驱动 | PyMySQL 1.0+ | MySQL 参数化查询，防 SQL 注入 |
| HTTP 客户端 | requests 2.31+ | 爬虫 HTTP 请求 |
| 浏览器自动化 | Selenium 4.15+ | 备用爬虫方案 |
| HTML 解析 | BeautifulSoup4 + lxml | 页面数据提取 |
| 数据处理 | pandas 2.x + numpy | 数据转换与统计分析 |
| 消息队列 | RabbitMQ + pika 1.3+ | 分布式任务调度 |
| AI 接口 | 智谱 GLM-4-Flash | 自然语言查询与数据分析 |
| 中文分词 | jieba (fallback 正则) | 词云关键词提取 |
| 容器化 | Docker Compose | MySQL + RabbitMQ 一键启动 |
| 前端 | Vanilla JS + HTML5/CSS3 | 无框架，轻量化 |
| 日志 | Python logging + 彩色输出 | 多进程安全，文件轮转 |

---

## 功能模块详解

### 身份认证与权限管理

**功能**：用户注册/登录、JWT Token 签发、基于角色的访问控制（RBAC）。

**角色体系**：

- `admin`：全部权限（用户管理、爬虫、数据读写、导出）
- `operator`：爬虫操作 + 数据管理权限
- `observer`：只读权限

**权限代码示例**：`crawler:start`、`crawler:view`、`data:export`、`user:list`、`user:update`

**核心代码** — JWT 装饰器 `backend/utils/decorators.py`：

```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = verify_token(token)           # 解析 JWT
        if not payload:
            return jsonify({'code': 401, 'message': '未授权'}), 401
        request.user_id = payload['user_id']
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 查询用户角色 → 角色权限 → 检查 permission_code
            if not has_permission(request.user_id, permission_code):
                return jsonify({'code': 403, 'message': '权限不足'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

**核心代码** — 登录接口 `backend/routes/auth.py`：

```python
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = hashlib.sha256(data.get('password').encode()).hexdigest()
    
    user = db.fetch_one(
        "SELECT * FROM sys_user WHERE username=%s AND password=%s AND status=1",
        (username, password)
    )
    if not user:
        return jsonify({'code': 401, 'message': '用户名或密码错误'})
    
    token = generate_token({'user_id': user['id'], 'username': username})
    return jsonify({'code': 200, 'data': {'token': token, 'user': user}})
```

---

### 分布式爬虫系统

**架构**：RabbitMQ 驱动的四阶段 Worker 流水线，支持自动重试（最多 3 次，指数退避）和死信队列。

**Worker 基类** `crawler/workers/base.py`：

```python
class BaseWorker:
    def start(self):
        """启动消息消费循环"""
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._on_message
        )
        self.channel.start_consuming()
    
    def _on_message(self, ch, method, properties, body):
        task = json.loads(body)
        retry_count = task.get('retry_count', 0)
        try:
            result = self.process(task)          # 子类实现具体逻辑
            self.forward(result)                 # 将结果发到下一个队列
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            if retry_count < 3:
                task['retry_count'] = retry_count + 1
                time.sleep(2 ** retry_count)    # 指数退避
                self.channel.basic_publish(exchange='', routing_key=self.queue_name, body=json.dumps(task))
            else:
                # 发送到死信队列
                self.channel.basic_publish(exchange='', routing_key='crawler_dead_letter', body=json.dumps(task))
            ch.basic_ack(delivery_tag=method.delivery_tag)
```

**反爬虫签名** `crawler/dy_xingtui/ReduxSiger.py`：

```python
class ReduxSigner:
    def sign_request(self, url, params):
        """生成抖音 API 请求签名"""
        timestamp = self._get_server_time()
        sign_str = f"{url}?{urlencode(sorted(params.items()))}&t={timestamp}"
        signature = hmac.new(self.secret_key.encode(), sign_str.encode(), hashlib.md5).hexdigest()
        return {
            'X-Minapp-Sign': signature,
            'sign': signature,
            't': timestamp
        }
```

**启动 Worker**：

```bash
# 启动所有 Worker（生产推荐）
python -m crawler.workers.run_workers

# 启动特定类型 Worker
python -m crawler.workers.run_workers --worker list
python -m crawler.workers.run_workers --worker detail
python -m crawler.workers.run_workers --worker analysis
```

---

### 数据清洗管道

**功能**：对原始爬取数据进行字段验证、数值解析、去重处理，写入清洁数据表。

**核心代码** — 中文数值解析（`goods.py`）：

```python
def parse_chinese_number(value):
    """解析中文数字表示，如 '2.5w' → 25000，'750-1000' → 875"""
    if not value:
        return 0
    value = str(value).strip()
    
    if '-' in value:                          # 范围值取均值
        parts = value.split('-')
        return (parse_chinese_number(parts[0]) + parse_chinese_number(parts[1])) / 2
    
    value = value.replace('+', '').replace(',', '')
    if 'w' in value or '万' in value:
        return float(value.replace('w', '').replace('万', '')) * 10000
    if 'k' in value or 'K' in value:
        return float(value.replace('k', '').replace('K', '')) * 1000
    
    return float(value) if value else 0
```

**清洗校验规则（`crawler/workers/cleaners/`）**：

| 字段 | 验证规则 |
|------|----------|
| `product_id` | 非空，唯一性去重 |
| `price` | 数值 > 0，解析万/千缩写 |
| `cos_fee` (佣金) | 解析百分比，0~100% |
| `sales_count` | 解析中文缩写，≥ 0 |
| `labels` | JSON 字符串解析 |
| `first_cid` | 一级分类 ID 合法性 |

**清洗 API**（需 `crawler:clean` 权限）：

```bash
# 清洗所有原始数据
POST /api/crawler/clean/all
{"batch_size": 100}

# 按表清洗
POST /api/crawler/clean/table/analysis_goods_list_raw
{"batch_size": 50}

# 查看各表清洗进度
GET /api/crawler/clean/status
```

---

### 商品数据接口

**功能**：分页查询、关键词搜索、分类筛选、收藏、统计。

**分类体系**（11 个一级分类，基于 `first_cid` 映射）：

> 食品饮料 / 家居日用 / 服饰鞋包 / 美妆个护 / 母婴用品 / 数码家电 / 饰品配件 / 运动户外 / 图书文具 / 汽车用品 / 其他

**核心代码** — 商品列表查询 `backend/routes/goods.py`：

```python
@goods_bp.route('/list', methods=['GET'])
@login_required
def get_goods_list():
    page     = int(request.args.get('page', 1))
    limit    = int(request.args.get('limit', 20))
    keyword  = request.args.get('keyword', '')
    category = request.args.get('category', '')
    sort_by  = request.args.get('sort_by', 'created_at')
    
    where_clauses, params = ['1=1'], []
    if keyword:
        where_clauses.append('title LIKE %s')
        params.append(f'%{keyword}%')
    if category:
        where_clauses.append('first_cid = %s')
        params.append(category)
    
    sql = f"""
        SELECT * FROM goods_list
        WHERE {' AND '.join(where_clauses)}
        ORDER BY {sort_by} DESC
        LIMIT %s OFFSET %s
    """
    params += [limit, (page - 1) * limit]
    goods = db.fetch_all(sql, params)
    return jsonify({'code': 200, 'data': goods, 'total': count})
```

---

### 热点预测引擎

**功能**：基于多维度加权评分模型，预测近期热点商品，支持词云关键词分析。

**评分公式**：

```
综合热点评分 =
    销量动量    × 0.30
  + 浏览增长    × 0.20
  + 达人增长    × 0.20
  + 佣金吸引力  × 0.15
  + 价格竞争力  × 0.15
```

**核心代码** `backend/routes/prediction.py`：

```python
def calculate_hot_score(goods):
    """计算商品热点综合评分（0~100）"""
    sales_score      = min(goods.get('sales_count', 0) / 10000 * 100, 100)
    creator_score    = min(goods.get('user_count', 0) / 100  * 100, 100)
    commission_score = min(goods.get('cos_fee', 0), 100)
    
    # 价格竞争力：价格越低分越高（相对同类均价）
    avg_price  = get_category_avg_price(goods['first_cid'])
    price_score = max(0, 100 - (goods['price'] / avg_price * 50)) if avg_price else 50
    
    return (
        sales_score      * 0.30 +
        sales_score      * 0.20 +   # 用销量增量近似浏览增长
        creator_score    * 0.20 +
        commission_score * 0.15 +
        price_score      * 0.15
    )
```

**词云生成**（优先 jieba，fallback 正则）：

```python
def generate_wordcloud_data(goods_list):
    """提取商品标题关键词并统计词频"""
    texts = [g['title'] for g in goods_list if g.get('title')]
    all_text = ' '.join(texts)
    
    try:
        import jieba
        words = jieba.cut(all_text)
    except ImportError:
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', all_text)  # 正则提取中文词
    
    # 过滤停用词，统计频率
    freq = Counter(w for w in words if len(w) >= 2 and w not in STOP_WORDS)
    return [{'word': w, 'value': c} for w, c in freq.most_common(100)]
```

---

### AI 智能助手

**功能**：集成智谱 GLM-4-Flash，支持自然语言提问，自动构建 SQL 查询，返回结构化数据洞察。

**会话管理**：每个用户可维护多个独立会话，消息记录持久化到数据库。

**核心代码** `backend/routes/ai_assistant.py`：

```python
@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data       = request.get_json()
    message    = data.get('message')
    session_id = data.get('session_id')
    
    # 构建数据库上下文（商品统计、近期热点）
    context = build_data_context()
    
    system_prompt = f"""你是一个抖音电商数据分析助手。
    当前数据库上下文：
    - 商品总数: {context['total_goods']}
    - 今日新增: {context['today_new']}
    - 热门品类: {context['top_categories']}
    
    请根据用户问题提供数据分析洞察。"""
    
    # 调用智谱 GLM-4-Flash
    client   = ZhipuAI(api_key=ZHIPU_API_KEY)
    response = client.chat.completions.create(
        model   = "glm-4-flash",
        messages = [
            {"role": "system", "content": system_prompt},
            *get_session_history(session_id),   # 携带历史记录
            {"role": "user",   "content": message}
        ]
    )
    
    reply = response.choices[0].message.content
    save_message(session_id, message, reply)    # 持久化聊天记录
    return jsonify({'code': 200, 'data': {'reply': reply}})
```

---

### 数据仪表盘

**功能**：实时概览、价格分布、趋势折线图、TOP 店铺、佣金排行、分类统计。

**接口清单**：

| 接口 | 功能 |
|------|------|
| `GET /api/dashboard/overview` | 商品总数、今日新增、平均价格、平均佣金 |
| `GET /api/dashboard/price_distribution` | 价格区间分布（柱状图数据） |
| `GET /api/dashboard/daily_trend` | 近 30 天新增趋势（折线图数据） |
| `GET /api/dashboard/top_shops` | TOP 10 店铺销量排行 |
| `GET /api/dashboard/commission_ranking` | 高佣金商品排行榜 |
| `GET /api/dashboard/category_stats` | 各分类商品数量与销售额占比 |

**大屏展示**（`frontend/bigscreen.html`）：支持全屏数据大屏，适合投屏展示。

---

### 数据导出

**功能**：将商品和分析数据导出为 CSV 或 JSON 文件，支持时间范围、分类、关键词过滤。

```bash
# 导出 CSV
GET /api/export/goods/csv?start_date=2026-01-01&end_date=2026-03-31&category=food

# 导出 JSON
GET /api/export/goods/json?keyword=蛋白粉&sort_by=sales_count
```

---

### 系统设置与用户管理

**功能**：管理员可创建/编辑用户，分配角色，启用/禁用账号。

**接口（需 admin 权限）**：

- `GET /api/settings/users` — 用户列表
- `POST /api/settings/users` — 创建用户
- `PUT /api/settings/users/<id>` — 更新用户信息/角色
- `DELETE /api/settings/users/<id>` — 禁用用户

---

## 数据库设计

### 核心表

```sql
-- 商品原始数据（爬虫写入）
CREATE TABLE analysis_goods_list_raw (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id VARCHAR(64) UNIQUE,
    title      VARCHAR(512),
    price      DECIMAL(10,2),
    image_url  TEXT,
    is_cleaned TINYINT DEFAULT 0,       -- 0=未清洗, 1=已清洗
    created_at DATETIME DEFAULT NOW()
);

-- 清洗后商品数据（供业务查询）
CREATE TABLE goods_list (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id   VARCHAR(64) UNIQUE,
    title        VARCHAR(512),
    price        DECIMAL(10,2),
    cos_fee      DECIMAL(5,2),          -- 佣金比例 %
    first_cid    VARCHAR(32),           -- 一级分类 ID
    labels       JSON,                  -- 商品标签
    sales_count  INT DEFAULT 0,
    user_count   INT DEFAULT 0,         -- 带货达人数
    created_at   DATETIME DEFAULT NOW()
);

-- 商品销售趋势（日粒度）
CREATE TABLE analysis_goods_trend (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    goods_id     VARCHAR(64),
    date         DATE,
    sales_count  INT,
    sales_amount DECIMAL(12,2),
    video_count  INT,
    live_count   INT,
    user_count   INT,
    INDEX idx_goods_date (goods_id, date)
);

-- 用户权限系统
CREATE TABLE sys_user (
    id       BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) UNIQUE,
    password VARCHAR(64),               -- SHA256
    nickname VARCHAR(64),
    email    VARCHAR(128),
    status   TINYINT DEFAULT 1          -- 1=启用, 0=禁用
);
```

### 完整表清单

| 类别 | 表名 |
|------|------|
| 商品 | `goods_list`, `analysis_goods_list_raw` |
| 趋势 | `analysis_goods_trend`, `analysis_goods_trend_raw` |
| 直播 | `analysis_live_list`, `analysis_live_trend` |
| 视频 | `analysis_video_sales`, `analysis_video_list`, `analysis_video_time` |
| 达人 | `analysis_user_list`, `analysis_user_top`, `analysis_kol_trend` |
| 系统 | `sys_user`, `sys_role`, `sys_permission`, `sys_user_role`, `sys_role_permission` |
| 日志 | `sys_operation_log`, `crawler_task_log` |
| AI   | `ai_chat_session`, `ai_chat_message` |

---

## 如何运行

### 前置条件

- Python 3.8+
- MySQL 8.0+
- RabbitMQ 3+（或通过 Docker Compose 一键启动）

### 方式一：Windows 一键启动（推荐）

```bash
# 双击或在终端执行
start.bat
```

脚本将自动：清理旧进程 → 检查虚拟环境 → 验证 MySQL 连接 → 启动 RabbitMQ → 启动 Flask（5001 端口）→ 启动 Worker → 打开浏览器

### 方式二：手动启动

```bash
# 1. 创建并激活虚拟环境
python -m venv .env
.env\Scripts\activate          # Windows
source .env/bin/activate       # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动基础服务（MySQL + RabbitMQ）
docker-compose up -d

# 4. 初始化数据库
mysql -h localhost -u root -p123456 dy_analysis_system < dy_analysis_system.sql

# 5. 启动 Flask 后端
python backend/app.py

# 6. 新开终端，启动 Worker
python -m crawler.workers.run_workers
```

### 方式三：Docker Compose 全量部署

```bash
docker-compose up -d
python backend/app.py
python -m crawler.workers.run_workers
```

### 访问系统

| 地址 | 说明 |
|------|------|
| `http://localhost:5001` | 主应用入口 |
| `http://localhost:5001/login.html` | 登录页 |
| `http://localhost:5001/dashboard.html` | 数据仪表盘 |
| `http://localhost:15672` | RabbitMQ 管理界面 |

**默认账号**：用户名 `admin` / 密码 `admin123`

### 环境变量配置

```bash
# 数据库
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=123456
export DB_NAME=dy_analysis_system

# RabbitMQ
export MQ_HOST=localhost
export MQ_PORT=5672
export MQ_USER=guest
export MQ_PASSWORD=guest

# API 密钥
export API_TOKEN=your_douyin_api_token
export ZHIPU_API_KEY=your_glm_api_key

# Flask
export JWT_SECRET=your-secret-key
```

### 启动爬虫任务

登录后，访问 **爬虫管理页** (`/crawler.html`) 配置任务参数，或直接调用 API：

```bash
# 启动商品列表爬取（爬取第 1~10 页）
POST /api/mq/start_list_crawler
Content-Type: application/json
Authorization: Bearer <your_jwt_token>

{
    "start_page": 1,
    "end_page": 10
}
```

---

## API 参考

所有接口前缀：`http://localhost:5001/api`

| 模块 | 方法 | 路径 | 功能 |
|------|------|------|------|
| **认证** | POST | `/auth/login` | 用户登录 |
| | POST | `/auth/register` | 用户注册 |
| | GET | `/auth/info` | 获取当前用户信息 |
| | POST | `/auth/change-password` | 修改密码 |
| **商品** | GET | `/goods/list` | 商品列表（分页/筛选） |
| | GET | `/goods/` | 商品详情 |
| | GET | `/goods/search` | 关键词搜索 |
| | GET | `/goods/by-category` | 按分类查询 |
| | GET | `/goods/stats` | 商品统计 |
| **爬虫** | POST | `/crawler/clean/all` | 清洗所有原始数据 |
| | GET | `/crawler/clean/status` | 清洗进度查看 |
| | POST | `/crawler/proxy` | 设置代理 |
| **仪表盘** | GET | `/dashboard/overview` | 概览统计 |
| | GET | `/dashboard/daily_trend` | 日趋势 |
| | GET | `/dashboard/category_stats` | 分类统计 |
| **预测** | GET | `/prediction/trending` | 热点商品预测 |
| | GET | `/prediction/wordcloud` | 词云数据 |
| **AI** | POST | `/ai/chat` | 发送消息 |
| | GET | `/ai/sessions` | 会话列表 |
| | GET | `/ai/messages/` | 聊天历史 |
| **导出** | GET | `/export/goods/csv` | 导出 CSV |
| | GET | `/export/goods/json` | 导出 JSON |
| **任务** | POST | `/mq/start_list_crawler` | 触发爬虫任务 |

---

## 日志与监控

**日志系统** (`logger.py`)：

- 控制台彩色输出，区分不同 Worker 和模块
- 按日期 + 大小自动轮转，存储在 `logs/` 目录
- Windows 多进程安全（文件锁处理）

```
logs/
├── app.log          # Flask 后端日志
├── crawler.log      # 爬虫主日志
├── worker_list.log  # ListWorker 日志
├── worker_detail.log
└── worker_analysis.log
```

**外部监控**：

| 监控点 | 地址 |
|--------|------|
| RabbitMQ 队列深度 | `http://localhost:15672` |
| MySQL 状态 | `SHOW PROCESSLIST;` |
| Worker 进程状态 | 系统进程管理器 |

---

## 安全设计

| 安全措施 | 实现方式 |
|---------|---------|
| 密码存储 | SHA256 哈希，不存明文 |
| 身份认证 | JWT HS256，24 小时过期 |
| 访问控制 | RBAC，细粒度权限代码 |
| SQL 注入防御 | PyMySQL 参数化查询 |
| 跨域控制 | Flask-CORS 白名单配置 |
| 反爬虫对抗 | Redux 签名 + Token 定期刷新 |
| 操作审计 | `sys_operation_log` 记录所有写操作 |

---

## 项目结构

```
DY_Predictionin/
├── backend/                   # Flask 后端
│   ├── app.py                # 应用入口
│   ├── config.py             # 后端配置
│   ├── models/               # 数据模型（User/Role/Permission/AIChat）
│   ├── routes/               # API 路由蓝图（12 个模块）
│   └── utils/                # JWT/装饰器/Mock 数据
├── crawler/                   # 爬虫系统
│   ├── dy_xingtui/           # 抖音小店爬虫（签名/爬取/回调）
│   ├── mq/                   # RabbitMQ 客户端封装
│   ├── workers/              # Worker 进程（List/Detail/Analysis/Clean）
│   ├── token_manager.py      # Token 管理
│   └── refresh_token.py      # Token 刷新
├── frontend/                  # 前端页面
│   ├── index.html            # 主应用
│   ├── dashboard.html        # 仪表盘
│   ├── crawler.html          # 爬虫管理
│   ├── ai_assistant.html     # AI 助手
│   ├── prediction.html       # 热点预测
│   ├── bigscreen.html        # 数据大屏
│   ├── products.html         # 商品列表
│   └── ...
├── config.py                  # 全局配置
├── logger.py                  # 日志系统
├── requirements.txt           # Python 依赖
├── docker-compose.yml         # Docker 编排
├── dy_analysis_system.sql     # 数据库初始化脚本
└── start.bat                  # Windows 一键启动
```

---


