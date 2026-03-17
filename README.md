# 抖音电商热点数据可视化分析系统

基于 Flask + Vue 3 + ECharts 的抖音电商数据分析平台，集成爬虫采集、数据分析、AI 智能助手、热点预测等功能。

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│  Flask API  │────▶│    MySQL     │
│ Vue3+Tailwind│     │ (Port 5001) │     │ (Port 3306)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  RabbitMQ   │
                    │ (Port 5672) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ListWorker   DetailWorker  AnalysisWorker
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 首页 | 商品数据总览、统计卡片、商品列表 |
| 数据仪表盘 | 销售趋势图、佣金排行、分类分布 |
| 热点预测 | AI 预测商品热度、词云展示 |
| 商品对比 | 多商品数据对比分析 |
| 我的收藏 | 收藏商品管理 |
| AI 智能助手 | 基于智谱AI的对话式数据分析 |
| 爬虫任务 | 任务管理、状态监控、历史记录 |
| 系统设置 | 用户管理、角色权限、操作日志、数据报告 |
| 数据大屏 | 全屏数据可视化展示 |

## 角色权限

| 角色 | 权限 |
|------|------|
| admin（管理员） | 全部功能 |
| operator（运营者） | 爬虫操作 + 数据查看 |
| viewer（观察者） | 仅查看数据 |

---

## Windows 部署指南

### 一、环境要求

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.9 ~ 3.12 | 后端运行环境 |
| MySQL | 8.0+ | 数据存储 |
| RabbitMQ | 3.x | 消息队列（爬虫任务调度） |
| Erlang | 25+ | RabbitMQ 运行依赖 |
| Git | 任意 | 拉取代码 |

### 二、安装依赖服务

#### 1. 安装 Python

1. 访问 https://www.python.org/downloads/ 下载 Python 3.10+
2. 安装时 **勾选 "Add Python to PATH"**
3. 验证：
```cmd
python --version
pip --version
```

#### 2. 安装 MySQL 8.0

**方式一：官方安装包（推荐）**
1. 下载：https://dev.mysql.com/downloads/installer/
2. 选择 "MySQL Server" 安装
3. 设置 root 密码为 `Dy@analysis2024`（或自定义，后续需修改配置）
4. 确保 MySQL 服务已启动（安装完成后默认自启）

**方式二：使用 Docker Desktop**
```cmd
docker run -d --name dy_mysql -p 3306:3306 ^
  -e MYSQL_ROOT_PASSWORD=Dy@analysis2024 ^
  -e MYSQL_DATABASE=dy_analysis_system ^
  mysql:8.0 --character-set-server=utf8mb4
```

验证连接：
```cmd
mysql -u root -p
```

#### 3. 安装 RabbitMQ

**方式一：官方安装（推荐）**

1. 安装 Erlang：https://www.erlang.org/downloads
   - 下载 Windows 安装包，一路 Next
2. 安装 RabbitMQ：https://www.rabbitmq.com/install-windows.html
   - 下载 Windows 安装包，一路 Next
3. 启用管理插件（以管理员身份运行 CMD）：
```cmd
cd "C:\Program Files\RabbitMQ Server\rabbitmq_server-3.13.7\sbin"
rabbitmq-plugins.bat enable rabbitmq_management
```
> 上面的路径中 `3.13.7` 替换为你安装的实际版本号

4. 重启 RabbitMQ 服务：
```cmd
net stop RabbitMQ && net start RabbitMQ
```
5. 验证：访问 http://localhost:15672 ，使用 guest / guest 登录

**方式二：使用 Docker**
```cmd
docker run -d --name dy_rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

#### 4. （可选）Docker Compose 一键启动 MySQL + RabbitMQ

如果你安装了 Docker Desktop，可以用项目自带的 `docker-compose.yml` 一键启动：
```cmd
docker-compose up -d
```
> 注意：Docker Compose 方式的 MySQL root 密码为 `123456`，需要修改配置文件中的 `DB_PASSWORD`。

---

### 三、项目部署

#### 1. 拉取代码

```cmd
git clone https://github.com/XXC-boop-xxz/DY_Predictionin.git
cd DY_Predictionin
```

#### 2. 创建虚拟环境并安装依赖

**方式一：使用脚本（推荐）**
```cmd
setup_env.bat
```

**方式二：手动操作**
```cmd
python -m venv .env
.env\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install cryptography sniffio -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 3. 修改配置（如需）

如果 MySQL 密码不是默认的 `Dy@analysis2024`，修改以下两个文件：

| 文件 | 字段 |
|------|------|
| `config.py` | `DB_PASSWORD` |
| `backend/config.py` | `DB_PASSWORD` |

或者通过环境变量设置（无需改代码）：
```cmd
set DB_PASSWORD=你的密码
```

#### 4. 导入数据库

```cmd
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS dy_analysis_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p dy_analysis_system < dy_analysis_system.sql
```

> 如果不导入 SQL 文件，首次启动后端时也会自动创建表结构和默认账号，但不包含示例商品数据。

#### 5. 启动服务

**方式一：一键启动**
```cmd
start.bat
```

**方式二：手动启动（推荐调试时使用）**

打开 **三个** CMD 窗口：

**窗口 1 — Flask 后端：**
```cmd
cd DY_Predictionin
.env\Scripts\activate.bat
python backend/app.py
```

**窗口 2 — 爬虫 Workers（可选，仅爬虫功能需要）：**
```cmd
cd DY_Predictionin
.env\Scripts\activate.bat
python -m crawler.workers.run_workers
```

**窗口 3 — 打开浏览器：**
```
http://localhost:5001
```

---

### 四、默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin123 | 管理员（全部权限） |

注册的新用户默认分配「观察者」角色。管理员可在「系统设置 → 用户管理 / 角色权限」中修改。

---

### 五、目录结构

```
DY_Predictionin/
├── backend/                  # Flask 后端
│   ├── app.py               # 应用入口（端口 5001）
│   ├── config.py            # 后端配置（JWT、数据库、MQ）
│   ├── models/              # 数据模型（User, Role, Permission）
│   ├── routes/              # API 路由
│   │   ├── auth.py          #   认证（登录/注册/改密码）
│   │   ├── goods.py         #   商品 CRUD
│   │   ├── goods_analysis.py#   商品分析数据
│   │   ├── mq.py            #   爬虫任务管理
│   │   ├── ai_assistant.py  #   AI 智能助手
│   │   ├── settings.py      #   系统设置（用户/角色管理）
│   │   ├── dashboard.py     #   仪表盘数据
│   │   ├── prediction.py    #   热点预测
│   │   ├── report.py        #   数据报告导出
│   │   └── ...
│   └── utils/               # 工具类（JWT、装饰器、Mock数据）
├── crawler/                  # 爬虫模块
│   ├── mq/                  # RabbitMQ 客户端封装
│   ├── workers/             # Worker 消费者
│   │   ├── base.py          #   Worker 基类（模板方法模式）
│   │   ├── list_worker.py   #   商品列表爬取
│   │   ├── detail_worker.py #   商品详情爬取
│   │   ├── analysis_worker.py#  数据分析爬取
│   │   ├── handlers/        #   分析接口 Handler
│   │   └── run_workers.py   #   Worker 启动入口
│   └── dy_xingtui/          # 抖音星图 API 封装
├── frontend/                 # 前端页面（Vue 3 + Tailwind CSS）
│   ├── index.html           # 主页（商品列表 + 侧边栏）
│   ├── login.html           # 登录页
│   ├── register.html        # 注册页
│   ├── home.html            # 营销落地页
│   ├── dashboard.html       # 数据仪表盘
│   ├── prediction.html      # 热点预测
│   ├── goods_detail.html    # 商品详情（图表分析）
│   ├── ai_assistant.html    # AI 智能助手
│   ├── crawler.html         # 爬虫任务管理
│   ├── settings.html        # 系统设置
│   ├── bigscreen.html       # 数据大屏
│   ├── compare.html         # 商品对比
│   ├── favorites.html       # 我的收藏
│   ├── css/                 # 样式文件
│   ├── js/                  # JS 工具
│   └── fonts/               # 字体文件
├── config.py                 # 全局配置（数据库、MQ、API Token）
├── logger.py                 # 日志模块
├── requirements.txt          # Python 依赖清单
├── docker-compose.yml        # Docker 编排（MySQL + RabbitMQ）
├── dy_analysis_system.sql    # 数据库初始化 SQL（含示例数据）
├── start.bat                 # Windows 一键启动脚本
├── setup_env.bat             # Windows 环境初始化脚本
└── start_mac.sh              # macOS 启动脚本
```

---

### 六、常见问题

#### Q: 启动报错 `cryptography package required`
```cmd
pip install cryptography
```

#### Q: AI 助手不工作
```cmd
pip install sniffio
```
并确认 `config.py` 中 `ZHIPU_API_KEY` 配置正确。

#### Q: 连接 MySQL 失败
1. 确认 MySQL 服务已启动（Windows 服务中查看 MySQL80）
2. 确认密码与 `config.py` 中的 `DB_PASSWORD` 一致
3. 确认数据库 `dy_analysis_system` 已创建

#### Q: 连接 RabbitMQ 失败
1. 确认 RabbitMQ 服务已启动（Windows 服务中查看 RabbitMQ）
2. 确认 http://localhost:15672 可访问
3. 默认账号 guest/guest 仅允许 localhost 连接

#### Q: 爬虫爬不到数据
爬虫需要有效的 API Token，当前 Token 可能已过期，需要在 `config.py` 中更新 `API_TOKEN`。

#### Q: 端口 5001 被占用
```cmd
netstat -ano | findstr :5001
taskkill /PID <进程ID> /F
```

#### Q: 页面打不开或样式异常
确保通过 http://localhost:5001 访问，不要直接用浏览器打开 HTML 文件。

---

### 七、技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Flask + Flask-SocketIO + Flask-CORS |
| 认证 | PyJWT (JSON Web Token) |
| 数据库 | MySQL 8.0 + PyMySQL |
| 消息队列 | RabbitMQ 3.x + Pika |
| 前端框架 | Vue 3 (CDN) + Tailwind CSS (CDN) |
| 图表 | ECharts 5 |
| AI | 智谱 AI (zhipuai SDK) |
| 爬虫 | Selenium + Requests |
