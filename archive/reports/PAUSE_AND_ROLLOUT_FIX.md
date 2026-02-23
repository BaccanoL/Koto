# 长任务暂停 + 灰度发布改进方案

## 问题概述

### 问题 1: 长任务暂停无效  
**症状**: 用户按下"暂停"按钮后，任务继续执行，系统卡住不动  
**根本原因**: 
- 原来的取消机制只是标记任务状态，不会中断正在执行的流式处理
- 在流式处理中没有检查点来判断任务是否被取消

### 问题 2: 灰度发布阶段太单调
**现状**: 3个阶段（10% → 50% → 100%）不够细致  
**需求**: 增加更多阶段（从3阶段改为7阶段）

---

## 解决方案

### 解决方案 1: 实现可中断的流式处理

#### 改动 1.1: task_scheduler.py - 添加取消检查机制

```python
class Task:
    def __init__(self, ...):
        # 新增：取消标志
        self._cancel_flag = False
    
    def is_cancelled(self) -> bool:
        """检查任务是否被取消"""
        return self._cancel_flag or self.status == TaskStatus.CANCELLED
    
    def mark_cancelled(self):
        """标记任务为已取消"""
        self._cancel_flag = True
        self.status = TaskStatus.CANCELLED

class TaskScheduler:
    def get_task(self, task_id: str) -> Task:
        """获取任务对象（用于在流式处理中检查取消状态）"""
        return self.tasks.get(task_id)

# 全局函数
def check_task_cancelled(task_id: str) -> bool:
    """快速检查任务是否被取消（用于流式处理）"""
    scheduler = get_task_scheduler()
    task = scheduler.get_task(task_id)
    if task:
        return task.is_cancelled()
    return False
```

**新增功能**:
- `is_cancelled()`: 检查任务是否被取消
- `mark_cancelled()`: 正确地标记任务为取消状态  
- `get_task()`: 在流式处理中快速获取任务对象
- `check_task_cancelled()`: 全局便利函数，供流式处理调用

#### 改动 1.2: document_feedback.py - 添加流式处理中的取消检查

```python
def full_annotation_loop_streaming(
    self,
    file_path: str,
    user_requirement: str = "",
    task_id: str = None  # 新增参数
):
    """为流式处理添加task_id参数"""
    from web.task_scheduler import check_task_cancelled
    
    # ===== Stage 1: 读取文档 =====
    if task_id and check_task_cancelled(task_id):
        yield {
            'stage': 'cancelled',
            'progress': 0,
            'message': '⏸️ 任务已被取消',
            'detail': ''
        }
        return
    
    # ... 读取文档代码 ...
    
    # ===== Stage 2: 分析生成标注建议 =====
    if task_id and check_task_cancelled(task_id):
        yield {
            'stage': 'cancelled',
            'progress': 0,
            'message': '⏸️ 任务已被取消',
            'detail': '分析前中断'
        }
        return
    
    # ... 分析代码 ...
    
    # ===== Stage 3: 应用标注到文档 =====
    if task_id and check_task_cancelled(task_id):
        yield {
            'stage': 'cancelled',
            'progress': 0,
            'message': '⏸️ 任务已被取消',
            'detail': '应用修改前中断'
        }
        return
```

**新增检查点**:
- 读取前检查 (5%)
- 分析前检查 (15%)
- 应用前检查 (55%)
- 应用过程中检查 (60%)

#### 改动 1.3: app.py - 传入 task_id 并处理取消事件

```python
# 从请求中获取task_id，用于支持取消操作
task_id = request.json.get('task_id')

# 迭代流式结果，传入task_id用于支持取消
for progress_event in feedback_system.full_annotation_loop_streaming(
    doc_path, 
    user_input, 
    task_id=task_id  # 新增参数
):
    # 处理任务取消
    if stage == 'cancelled':
        cancelled = True
        yield f"data: {json.dumps({'type': 'info', 'message': '⏸️ 任务已取消', 'detail': '用户中止了处理'})}\n\n"
        break
```

**使用流程**:
1. 前端发送 task_id 到后端
2. 用户点击"暂停"，调用 `/api/tasks/<task_id>/cancel` API
3. cancel_task() 立即标记任务为 CANCELLED
4. 流式处理在下一个检查点发现任务被取消
5. 立即停止处理并返回 'cancelled' 事件
6. 前端收到 'cancelled' 事件，显示暂停信息

---

### 解决方案 2: 灰度发布阶段优化

#### 改动 2.1: DEPLOYMENT_CHECKLIST.md - 从3阶段改为7阶段

**旧方案** (3阶段):
```
10% → 50% → 100%
```

**新方案** (7阶段):
```
5% → 10% → 15% → 25% → 50% → 75% → 100%
```

**各阶段详情**:

| 阶段 | 用户百分比 | 主要验证内容 | 监控周期 |
|------|-----------|-----------|---------|
| 1. 金丝雀测试 | 5% | 内部员工、基础功能验证 | 6-12h |
| 2. 早期用户 | 10% | 流式反馈效果、初步反馈 | 12-24h |
| 3. 小规模推广 | 15% | 暂停机制工作正常 | 12-24h |
| 4. 中等规模 | 25% | 现实负载、资源使用 | 24h |
| 5. 大规模推广 | 50% | 长时间稳定性、内存泄漏 | 24-48h |
| 6. 接近全量 | 75% | 高并发表现、取消机制稳定 | 12-24h |
| 7. 全量发布 | 100% | 所有用户、持续监控 | 持续 |

**总周期**: 约 5-7 天

---

## 技术亮点

### 1. 非阻塞取消机制
- ✅ 取消操作能在毫秒内完成（不需要等待当前操作）
- ✅ 多个检查点确保及时响应（不会等太久）
- ✅ 流式处理中的每个关键阶段都有检查

### 2. 完整的生命周期管理
```
任务创建 → 开始执行 → 检查点 1 → 检查点 2 → 检查点 3 → 任务完成
               ↓
        用户点击"暂停"
               ↓
           标记取消
               ↓
        下一检查点发现取消
               ↓
          立即停止处理
               ↓
        返回 'cancelled' 事件
               ↓
        前端显示"已暂停"状态
```

### 3. 细致的灰度发布
- 每个阶段都有明确的验证目标
- 允许从小用户量逐步扩大
- 每个阶段都有充分的监控时间

---

## 使用指南

### 前端集成

#### 步骤 1: 发送 task_id

```javascript
// 当开始任务时，获取或生成 task_id
const taskId = generateTaskId(); // 或从后端获取

const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: userInput,
        task_type: 'DOC_ANNOTATE',
        task_id: taskId  // 重要：传入 task_id
    })
});
```

#### 步骤 2: 监听 'cancelled' 事件

```javascript
const eventSource = new EventSource(url);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'info' && data.message.includes('已取消')) {
        // 任务已取消
        progressBar.style.display = 'none';
        statusText.textContent = '任务已暂停';
        pauseButton.disabled = true;
    }
};
```

#### 步骤 3: 实现暂停按钮

```javascript
pauseButton.addEventListener('click', () => {
    // 调用取消 API
    fetch(`/api/tasks/${taskId}/cancel`, {
        method: 'POST'
    }).then(res => {
        if (res.ok) {
            console.log('暂停请求已发送');
            // 前端会在监听到 'cancelled' 事件时更新 UI
        }
    });
});
```

### 后端集成

#### 步骤 1: 确保传入 task_id

```python
# 在 full_annotation_loop_streaming 调用时传入 task_id
for progress_event in feedback_system.full_annotation_loop_streaming(
    doc_path, 
    user_input, 
    task_id=task_id
):
```

#### 步骤 2: 处理取消事件

```python
if stage == 'cancelled':
    cancelled = True
    yield f"data: {json.dumps({'type': 'info', 'message': '⏸️ 任务已取消'})}\n\n"
    break
```

---

## 验证清单

### 功能验证
- [ ] 长任务运行中能够被暂停
- [ ] 暂停后系统不会卡住
- [ ] 前端能够收到 'cancelled' 事件
- [ ] 可以立即开始新任务（无需等待旧任务完全清理）
- [ ] DOC_ANNOTATE 任务能够在任意阶段被暂停

### 灰度发布验证
- [ ] 5% 用户无异常（金丝雀测试）
- [ ] 10% 用户反馈良好（早期用户）
- [ ] 15% 用户暂停机制工作正常
- [ ] 25% 用户负载正常
- [ ] 50% 用户长时间稳定
- [ ] 75% 用户高并发稳定
- [ ] 100% 用户全量上线

### 监控指标
- [ ] 取消响应时间 < 500ms
- [ ] 暂停后内存释放 > 80%
- [ ] 流式处理成功率 > 99%
- [ ] SSE 连接稳定率 > 99.5%

---

## 回滚方案

如果在任何灰度阶段出现严重问题：

1. **立即停止扩大** (5 分钟内)
   - 不再向新用户推出

2. **通知受影响用户** (15 分钟内)
   - 发送提醒，建议暂停此功能

3. **切换回前一个版本** (30 分钟内)
   - 恢复到上一个稳定版本
   - 如果是代码问题，回退代码更新
   - 如果是配置问题，调整配置

4. **根因分析** (24 小时内)
   - 分析为什么会出现此问题
   - 制定修复方案
   - 加强测试覆盖

5. **修复后重新灰度**
   - 从 5% 开始重新灰度
   - 更严格的监控

---

## 相关文件

- `web/task_scheduler.py` - 任务调度器（新增取消检查）
- `web/document_feedback.py` - 文档反馈系统（新增流式处理取消支持）
- `web/app.py` - 主应用（新增 task_id 参数和取消事件处理）
- `DEPLOYMENT_CHECKLIST.md` - 部署清单（新增7阶段灰度发布方案）

---

## 常见问题

### Q1: 为什么需要多个检查点？
**A**: 不同的操作执行时间不同。如果只在开始检查，长任务会继续执行很久。多个检查点确保最多等待几秒就能响应。

### Q2: 能否一次性检查而不是多个检查点？
**A**: 不行。假设在"分析文档"阶段需要 30 秒，用户等不了这么久。多个检查点能让应用在任何阶段都能快速响应。

### Q3: 灰度发布为什么需要 7 个阶段？
**A**: 
- 5% 找到最严重的问题（金丝雀测试）
- 10% 验证基础功能
- 15% 验证暂停机制（新功能）
- 25% 验证中等负载
- 50% 验证长时间稳定性
- 75% 验证高并发
- 100% 全量上线

两个阶段间隔短（12-24 小时），能及时发现问题。

### Q4: 如果灰度过程中出现问题怎么办？
**A**: 立即停止在当前阶段扩大，通知受影响用户，回滚到前一版本，分析根因，修复后重新灰度。

---

## 更新时间

**实现日期**: 2024-2-11  
**修改文件数**: 3  
**新增代码行数**: ~50 行（task_scheduler.py）+ ~50 行（document_feedback.py）+ ~30 行（app.py）  
**灰度发布文档更新**: 从 3 阶段 更新为 7 阶段
