# 忘记密码 → 管理员通知 → 重置密码

用户在登录页点击"忘记密码"后，提交重置申请（仅需填用户名+原因），请求发送到管理员。管理员在「系统设置」的新"消息"Tab 中查看待处理请求，并一键重置密码。侧边栏的"系统设置"和"通知"文字右上角显示未处理请求数的红色角标。

## Proposed Changes

### 数据库

#### [NEW] `sys_password_reset_request` 表

在 [base.py](file:///e:/desktop/test/dy/yyyyc/backend/models/base.py) 的 [init_tables()](file:///e:/desktop/test/dy/yyyyc/backend/models/base.py#22-206) 中新增建表 SQL：

```sql
CREATE TABLE IF NOT EXISTS sys_password_reset_request (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL COMMENT '申请重置的用户名',
    reason     VARCHAR(500) DEFAULT '' COMMENT '申请原因',
    status     TINYINT      DEFAULT 0 COMMENT '0=待处理 1=已处理 2=已拒绝',
    handler_id INT          NULL COMMENT '处理人(管理员)ID',
    handled_at TIMESTAMP    NULL COMMENT '处理时间',
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='密码重置申请表';
```

在base.py的init_tables()中新增表Sql：

```sql
	CREATE TABLE IF NOT EXISTS sys_notification (
    	id INT AUTO_INCREMENT PRIMARY KEY,
    	user_id INT NULL COMMENT '目标用户ID',
    	type VARCHAR(20) DEFAULT 'info' COMMENT '通知类型',
   	 	title VARCHAR(200) NOT NULL COMMENT '通知标题',
    	content TEXT COMMENT '通知内容',
   		source VARCHAR(50) DEFAULT '' COMMENT '来源',
    	is_read TINYINT DEFAULT 0 COMMENT '0未读 1已读',
    	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   	    INDEX idx_user_id (user_id),
    	INDEX idx_is_read (is_read)
	) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统通知表';
   		
```

---





### 后端 API

#### [MODIFY] [auth.py](file:///e:/desktop/test/dy/yyyyc/backend/routes/auth.py)

- **改造** 现有的 `POST /api/auth/reset-password` 路由：改为**提交重置申请**（无需登录）
  - 请求体：`{ "username": "xxx", "reason": "忘记了密码" }`
  - 逻辑：验证用户名存在 → 插入 `sys_password_reset_request` 表（status=0）→ 返回成功提示
  - 不再直接修改密码

#### [NEW] `GET /api/auth/reset-request-status`

- **功能**：允许用户在登录页查询自己的申请状态，并获取管理员设置的临时密码。
- **请求参数**：`username`
- **逻辑**：查询 `sys_password_reset_request` 表中该用户最新的记录。
- **返回结果**：
  - 待处理：`{ "status": 0, "message": "申请正在处理中，请稍后再试" }`
  - 已通过：`{ "status": 1, "message": "申请已通过", "temporary_password": "xxxx" }` （仅显示一次或提示联系管理员）
    - *优化建议*：为了安全，管理员重置时发出的站内通知对无法登录的用户无用。查询接口将返回管理员设置的那个密码（例如默认的123456）。
  - 已拒绝：`{ "status": 2, "message": "申请已被拒绝，请联系管理员" }`

#### [MODIFY] [settings.py](file:///e:/desktop/test/dy/yyyyc/backend/routes/settings.py)

新增 3 个管理员专用 API：

1. **`GET /api/settings/reset_requests`** — 获取重置申请列表（分页，支持 `status` 筛选）
2. **`POST /api/settings/reset_requests/<id>/handle`** — 处理申请：接收 `{ "action": "approve", "password": "123456" }` 或 `{ "action": "reject" }`
   - approve：重置该用户密码 + 更新申请状态为 1 + 记录操作日志
   - reject：更新状态为 2
3. **`GET /api/settings/reset_requests/pending_count`** — 返回待处理请求数 `{ "code": 0, "data": { "count": 5 } }`

---

### 前端

#### [MODIFY] [login.html](file:///e:/desktop/test/dy/yyyyc/frontend/login.html)

- 改造"忘记密码"弹窗：
  - 分为两个 Tab："提交申请" 和 "**查询进度**"
  - 提交申请部分：移除"新密码"和"确认密码"输入框，保留"用户名"输入框，新增"原因"文本域（可选）。
  - **查询进度部分**：只需输入用户名。点击查询后显示申请状态。
  - 如果状态是"已通过"，直接显示：**您的密码已被重置为：xxxx，请立即登录并修改密码。**
  - 登录成功后触发强制修改密码流程。

#### [MODIFY] [settings.html](file:///e:/desktop/test/dy/yyyyc/frontend/settings.html)

1. **新增"消息"Tab**（仅管理员可见，插入到 `allTabs` 数组中）
   - Tab 内容：一个请求列表表格（用户名、原因、状态、提交时间、操作按钮）
   - 操作按钮："重置密码"（弹窗输入新密码，默认123456）和"拒绝"
   - 已处理的请求显示处理状态标签

2. **侧边栏角标**：
   - "系统设置"菜单项旁添加红色圆形角标，显示待处理请求数
   - 页面加载时调用 `GET /api/settings/reset_requests/pending_count` 获取数据
   - 角标样式：红色圆形，白色字体，`position: relative` + 绝对定位

3. **"消息"Tab 标签上也显示角标**：在 Tab 按钮文字旁显示未处理数量

#### 其他页面侧边栏角标

以下页面的侧边栏"系统设置"链接旁也需添加角标（仅管理员可见）：
- [index.html](file:///e:/desktop/test/dy/yyyyc/frontend/index.html)
- [dashboard.html](file:///e:/desktop/test/dy/yyyyc/frontend/dashboard.html)
- [prediction.html](file:///e:/desktop/test/dy/yyyyc/frontend/prediction.html)
- [compare.html](file:///e:/desktop/test/dy/yyyyc/frontend/compare.html)
- [favorites.html](file:///e:/desktop/test/dy/yyyyc/frontend/favorites.html)
- [ai_assistant.html](file:///e:/desktop/test/dy/yyyyc/frontend/ai_assistant.html)
- [crawler.html](file:///e:/desktop/test/dy/yyyyc/frontend/crawler.html)

每个页面 `onMounted` 中判断 [isAdmin](file:///e:/desktop/test/dy/yyyyc/frontend/js/sidebar_badge.js#9-16)，如果是管理员则调用 pending_count API 并渲染角标。

---

## Verification Plan

### 手动测试步骤

1. **用户提交重置申请**
   - 打开 [login.html](file:///e:/desktop/test/dy/yyyyc/frontend/login.html) → 点击"忘记密码?" → 填写用户名和原因 → 点击"提交申请"
   - 预期：Toast 提示"申请已提交"，弹窗关闭

2. **管理员查看并处理请求**
   - 用管理员账号登录 → 进入"系统设置" → 点击"消息"Tab
   - 预期：看到刚提交的申请，操作列有"重置密码"和"拒绝"按钮
   - 点击"重置密码" → 确认弹窗中输入新密码 → 确认
   - 预期：Toast 提示成功，申请状态变为"已处理"

3. **角标验证**
   - 管理员登录后在任意页面侧边栏"系统设置"旁应看到红色角标（数字为待处理数）
   - 处理完所有请求后角标消失
   - 非管理员用户不显示角标

4. **用户用新密码登录**
   - 管理员重置后，用户用新密码登录
   - 预期：登录成功
