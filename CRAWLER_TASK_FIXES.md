# 爬虫任务历史和商品去重问题修复报告

**修复日期**: 2026-03-22
**状态**: ✅ 已完成

---

## 问题分析

### 🔴 问题 1: 任务历史短暂显示后消失

**原因**:
- 前端使用本地内存存储任务历史 (`taskHistory.value`)
- 离开页面后内存清空，历史记录消失
- 没有从数据库查询任务记录

**影响**: 用户无法查看历史任务记录和执行状态

---

### 🔴 问题 2: 看不到爬虫任务进度和详情

**原因**:
- `loadDbTaskLogs()` 只在页面加载时调用一次
- 任务发送后没有刷新，所以看不到 Worker 的执行状态
- 前端没有自动更新任务状态

**影响**: 用户无法跟踪任务执行进度

---

### 🔴 问题 3: 启动爬虫任务后没有爬取到新商品

**原因**:
- Redis 中保存了之前爬取的商品 ID (去重缓存)
- 重复爬取相同页码时，所有商品都被识别为已存在
- 用户没有清除缓存的方式

**影响**: 用户无法重新爬取商品，认为爬虫失败

---

## 修复方案

### ✅ 修复 1: 任务历史持久化 + 自动刷新

**前端修改** (`frontend/crawler.html`):

```javascript
// 修改前：直接添加到本地内存
addTask('list', params, taskId, success)

// 修改后：发送成功后从数据库加载
if (res.success) {
    setTimeout(() => loadDbTaskLogs(), 500)  // 立即加载
}

// 添加自动刷新
setInterval(() => {
    loadDbTaskLogs()  // 每 5 秒刷新一次
}, 5000)
```

**效果**:
- ✅ 任务发送后立即从数据库加载最新记录
- ✅ 每 5 秒自动刷新一次，保持最新状态
- ✅ 离开页面后回来，记录仍然存在（从数据库查询）

---

### ✅ 修复 2: Redis 去重缓存管理

**后端添加的新 API**:

#### 1️⃣ 清除去重缓存
```
POST /api/crawler/dedup/clear
Body: {}
Response: {
    "success": true,
    "message": "已清除 150 个去重缓存",
    "data": {"deleted_count": 150}
}
```

#### 2️⃣ 查看缓存状态
```
GET /api/crawler/dedup/status
Response: {
    "success": true,
    "data": {
        "redis_status": "connected",
        "total_keys": 5,
        "total_items": 1500,
        "keys_info": {
            "crawler:seen_products": 1500
        }
    }
}
```

**前端添加的新功能**:

- 🎨 Redis 去重缓存管理面板
- 📊 实时显示缓存项数和连接状态
- 🔄 "检查状态"按钮 - 查询最新缓存信息
- 🗑️ "清除所有去重缓存"按钮 - 一键清除所有缓存

**使用场景**:
```
用户流程：
1. 点击"检查状态" → 看到当前有 1500 个缓存商品
2. 点击"清除所有去重缓存" → 缓存被清除
3. 重新启动"列表爬取" → 可以再次爬取相同商品
```

---

## 修复前后对比

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 任务历史可见性 | ❌ 离开页面就消失 | ✅ 永久保存，自动刷新 |
| 任务进度追踪 | ❌ 看不到执行状态 | ✅ 每 5 秒更新一次 |
| 任务详情查看 | ⚠️ 代码存在但无法更新 | ✅ 可实时查看 |
| 商品重复问题 | ❌ 无法清除 Redis | ✅ 提供清除按钮 |
| 缓存管理 | ❌ 黑盒操作 | ✅ 可视化管理面板 |

---

## 技术实现细节

### 前端改进

**文件**: `frontend/crawler.html`

1. **移除本地 addTask 调用**:
   ```javascript
   // 旧：addTask('list', params, taskId, success)
   // 新：from database
   ```

2. **任务发送后立即刷新**:
   ```javascript
   async function startListCrawler() {
       const res = await apiFetch('/mq/start_list_crawler', {...})
       if (res.success) {
           setTimeout(() => loadDbTaskLogs(), 500)  // 重新加载
       }
   }
   ```

3. **定时自动刷新**:
   ```javascript
   setInterval(() => loadDbTaskLogs(), 5000)  // 每 5 秒
   ```

4. **新增去重缓存管理**:
   - `checkRedisStatus()` - 查询缓存状态
   - `clearRedisDedup()` - 清除缓存
   - 新增 UI 面板显示统计信息

### 后端改进

**文件**: `backend/routes/crawler.py`

1. **新增清除缓存 API**:
   ```python
   @crawler_bp.route('/dedup/clear', methods=['POST'])
   def clear_redis_dedup():
       # 清除所有 crawler:seen_products* key
   ```

2. **新增缓存状态 API**:
   ```python
   @crawler_bp.route('/dedup/status', methods=['GET'])
   def get_dedup_status():
       # 查询 Redis 中的缓存统计
   ```

3. **权限控制**:
   - 清除缓存需要 `crawler:clean` 权限
   - 查看缓存需要 `crawler:view` 权限

---

## 使用指南

### 场景 1: 重新爬取相同商品

```
1. 进入 爬虫任务 页面
2. 找到 "商品去重缓存 (Redis)" 区域
3. 点击 "检查状态" 查看当前缓存
4. 点击 "清除所有去重缓存"
5. 重新启动 "列表爬取" 或 "商品详情爬取"
6. 新的爬取任务会处理所有商品，包括之前重复的
```

### 场景 2: 监控任务执行状态

```
1. 启动爬虫任务后，任务自动添加到列表
2. 无需手动刷新，每 5 秒自动更新一次
3. 可以看到：
   - 发送状态（已发送/发送失败）
   - 执行状态（等待/执行中/已完成/失败）
   - 执行进度（如果正在执行）
   - 执行结果（如果已完成）
4. 点击 "详情" 查看完整的任务执行信息
```

---

## 性能影响

- ⏱️ **自动刷新间隔**: 5 秒（可在代码中调整）
- 📊 **API 调用**: `loadDbTaskLogs()` 每次查询最后 50 条记录
- 💾 **内存占用**: 最小化（从数据库动态加载）
- 🚀 **响应速度**: < 500ms（通常）

---

## 后续优化建议

1. **添加刷新间隔配置**
   ```javascript
   const REFRESH_INTERVAL = 5000  // 可配置
   ```

2. **支持自定义清除 Key 模式**
   ```
   POST /api/crawler/dedup/clear
   Body: {"key_pattern": "crawler:seen_products:*"}
   ```

3. **添加定时自动清除**
   - 每天凌晨 3 点自动清除去重缓存
   - 或设置 TTL (Time To Live)

4. **任务历史分页加载**
   - 当任务数量很多时，支持分页查询
   - 减轻数据库和前端压力

---

## 测试清单

- [x] 任务发送后立即显示在历史中
- [x] 离开页面后回来，任务记录仍存在
- [x] 任务执行状态每 5 秒自动更新
- [x] 点击任务 "详情" 可查看完整信息
- [x] Redis 连接成功时显示缓存统计
- [x] Redis 连接失败时显示提示信息
- [x] 清除缓存后可重新爬取相同商品
- [x] 权限检查正确 (需要 crawler:clean 权限)

---

**修复提交**: 4813c31 - Fix: 修复爬虫任务历史和商品去重问题
**文件修改**: 2 files changed, 175 insertions(+)
