# 🤖 Koto Adaptive Agent 系统 - 部署与使用指南

## 📋 系统概述

**Koto Adaptive Agent** 是一个智能自适应任务处理系统，扩展了 Koto 应用的能力，使其能够：

- ✅ **自动理解任务** - 解析自然语言请求并分类
- ✅ **智能拆分** - 将复杂任务分解为可执行步骤
- ✅ **动态工具调度** - 自动选择和调用适当的工具
- ✅ **自动依赖管理** - 自动检测和安装缺失的包
- ✅ **错误恢复** - 智能处理失败并尝试恢复
- ✅ **实时反馈** - 流式事件返回执行进度

---

## 🚀 部署状态

### ✅ 已完成

| 组件 | 文件 | 状态 | 功能 |
|------|------|------|------|
| **核心引擎** | `web/adaptive_agent.py` | ✅ 550+ LOC | 任务分析、执行、管理 |
| **API 层** | `web/adaptive_agent_api.py` | ✅ 280+ LOC | 7 个 REST/SSE 端点 |
| **应用集成** | `web/app.py` | ✅ 修改完成 | 已注册蓝图，启用 Gemini AI |
| **文档** | `ADAPTIVE_AGENT_GUIDE.md` | ✅ 完成 | 详细使用指南 |
| **测试** | `test_adaptive_agent_v2.py` | ✅ 7/7 通过 | 功能验证套件 |

### 📊 覆盖的功能

```
✅ 任务分析器           → 自动分类 9 个任务类型
✅ 工具注册表           → 6 个内置工具 + 可扩展
✅ Agent 初始化         → 完整实例化
✅ 任务分析             → 生成执行计划
✅ 事件系统             → 8 种事件回调
✅ 任务序列化           → JSON 格式保存
✅ 上下文系统           → 运行时变量传递
```

---

## 📂 文件结构

```
Koto/
├── web/
│   ├── app.py                          # 主应用 (已修改)
│   ├── adaptive_agent.py               # ✨ 核心系统 (新建)
│   ├── adaptive_agent_api.py          # ✨ API 层 (新建)
│   ├── ... (其他现有模块)
│
├── ADAPTIVE_AGENT_GUIDE.md            # ✨ 详细指南 (新建)
├── test_adaptive_agent_v2.py          # ✨ 测试套件 (新建)
└── ... (项目其他文件)
```

---

## 🔧 快速开始

### 1. 验证安装

```bash
# 在 Koto 项目目录中运行
python test_adaptive_agent_v2.py

# 预期输出
# 🎉 所有功能验证通过!
# 📈 通过: 7/7
```

### 2. 启动应用

```bash
# 启动 Flask 应用（如果尚未启动）
python web/app.py
```

### 3. 基本使用

#### 方法 A: Python 代码集成

```python
from web.adaptive_agent import AdaptiveAgent

# 创建 Agent 实例
agent = AdaptiveAgent()

# 处理请求
task = agent.process("帮我排序一个列表")

# 检查结果
print(f"状态: {task.status.value}")
print(f"耗时: {task.duration:.2f}s")
```

#### 方法 B: REST API 调用

```bash
# 同步请求
curl -X POST http://localhost:5000/api/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "request": "计算前 10 个斐波那契数列"
  }'

# 流式请求 (SSE)
# 监听 POST /api/agent/process-stream 获取实时更新
```

#### 方法 C: 前端集成

```javascript
// 使用流式处理获取实时反馈
async function processWithStream(request) {
  const response = await fetch('/api/agent/process-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.substring(6));
        console.log(`事件: ${event.type}`, event.data);
      }
    }
  }
}
```

---

## 📡 API 端点文档

### 1️⃣ 获取工具列表
```http
GET /api/agent/tools

Response:
{
  "success": true,
  "tools": {
    "python_exec": { ... },
    "file_ops": { ... },
    ...
  },
  "count": 6
}
```

### 2️⃣ 同步处理请求
```http
POST /api/agent/process

Body:
{
  "request": "用户请求",
  "context": { "key": "value" }
}

Response:
{
  "success": true,
  "task": {
    "task_id": "task_xxx",
    "status": "success",
    "duration": 2.5,
    ...
  }
}
```

### 3️⃣ 流式处理请求
```http
POST /api/agent/process-stream

Body: { "request": "..." }

Response (SSE Stream):
data: {"type": "task_started", "data": {...}}
data: {"type": "step_started", "data": {...}}
data: {"type": "task_final", "data": {...}}
```

### 4️⃣ 仅分析请求
```http
POST /api/agent/analyze

Response:
{
  "success": true,
  "task_type": "code_generation",
  "steps": [ ... ],
  "required_packages": [ ... ]
}
```

### 5️⃣ 获取执行历史
```http
GET /api/agent/history

Response:
{
  "success": true,
  "history": [ ... ],
  "count": 5
}
```

### 6️⃣ 获取 Agent 状态
```http
GET /api/agent/status

Response:
{
  "success": true,
  "agent": {
    "initialized": true,
    "tools_available": 6,
    "tasks_completed": 5
  }
}
```

### 7️⃣ 注册自定义工具
```http
POST /api/agent/register-tool

Body:
{
  "tool_id": "my_custom_tool",
  "function": "...",
  "definition": { ... }
}
```

---

## 🛠 支持的任务类型

| 类型编号 | 类型名称 | 描述 | 关键字 | 默认工具 |
|--------|--------|------|--------|---------|
| 1 | CODE_GEN | 代码生成 | 代码、脚本 | python_exec |
| 2 | DATA_PROCESS | 数据处理 | 数据、CSV | data_process |
| 3 | FILE_CONVERT | 格式转换 | 转换、导出 | file_ops |
| 4 | WEB_SCRAPE | 网页爬取 | 爬取、URL | network_ops |
| 5 | IMAGE_PROC | 图像处理 | 图片、缩放 | image_proc |
| 6 | MATH_SOLVE | 数学计算 | 计算、求和 | python_exec |
| 7 | TEXT_PROC | 文本处理 | 文本、提取 | 文本工具 |
| 8 | SYSTEM_OP | 系统操作 | 打开、运行 | 系统命令 |
| 9 | UNKNOWN | 未知 | (自动推断) | (AI 决定) |

---

## 🧰 内置工具详情

### 1. python_exec - Python 代码执行
```json
{
  "name": "python_exec",
  "description": "执行 Python 代码片段",
  "dependencies": [],
  "can_chain": true
}
```

### 2. file_ops - 文件操作
```json
{
  "name": "file_ops",
  "description": "通用文件操作（读写、转换等）",
  "file_handler": true,
  "file_extensions": [".txt", ".json", ".csv", ".md"],
  "can_chain": true
}
```

### 3. package_mgmt - 包管理
```json
{
  "name": "package_mgmt",
  "description": "自动安装和管理 Python 包",
  "can_chain": true
}
```

### 4. data_process - 数据处理
```json
{
  "name": "data_process",
  "description": "数据处理和转换（支持 pandas）",
  "dependencies": ["pandas", "numpy"],
  "file_extensions": [".csv", ".xlsx", ".json"],
  "can_chain": true
}
```

### 5. image_proc - 图像处理
```json
{
  "name": "image_proc",
  "description": "图像处理（支持 PIL/Pillow）",
  "dependencies": ["pillow"],
  "file_extensions": [".png", ".jpg", ".jpeg", ".gif", ".bmp"],
  "can_chain": true
}
```

### 6. network_ops - 网络操作
```json
{
  "name": "network_ops",
  "description": "网络请求和数据爬取",
  "dependencies": ["requests", "beautifulsoup4"],
  "can_chain": true
}
```

---

## 📊 事件系统

系统通过以下 8 种事件进行回调通知：

| 事件类型 | 触发时机 | 数据包含 |
|--------|---------|--------|
| `task_started` | 任务开始 | task_id, request |
| `step_started` | 步骤开始 | step_id, description |
| `installing_packages` | 安装依赖包 | packages |
| `step_completed` | 步骤完成 | step_id, status, result |
| `error_occurred` | 发生错误 | step_id, error |
| `recovery_attempt` | 尝试恢复 | step_id, strategy |
| `task_final` | 任务完成 | task_id, status, duration |
| `task_completed` | 任务完全结束 | task_id, result |

---

## ⚙️ 配置选项

### 应用级配置

在 `web/app.py` 中修改：

```python
# 启用/禁用 AI 辅助分析
USE_GEMINI_AI = True

# 设置默认超时时间（秒）
DEFAULT_TIMEOUT = 300

# 设置最大并发任务数
MAX_CONCURRENT_TASKS = 10
```

### Agent 级配置

```python
agent = AdaptiveAgent(
    gemini_client=my_client,      # 可选：Gemini 客户端
    max_retries=3,                # 失败重试次数
    timeout=300                   # 默认超时
)
```

---

## 🔍 监控和调试

### 启用日志记录

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('adaptive_agent')
```

### 查看执行历史

```python
# 获取最后 10 个任务
agent = AdaptiveAgent()
tasks = agent.execution_history[-10:]

for task in tasks:
    print(f"Task {task.task_id}: {task.status.value} in {task.duration}s")
```

### 性能监控

```python
# 计算平均执行时间
avg_duration = sum(
    t.duration for t in agent.execution_history
) / len(agent.execution_history)

print(f"平均执行时间: {avg_duration:.2f}s")
```

---

## 🧪 测试和验证

### 运行测试套件

```bash
# 完整功能测试
python test_adaptive_agent_v2.py

# 预期结果
# ✅ 任务分析器
# ✅ 工具注册表
# ✅ Agent 初始化
# ✅ 任务分析
# ✅ 事件系统
# ✅ 任务序列化
# ✅ 上下文系统
# 📈 通过: 7/7
```

### 手动测试示例

```python
from web.adaptive_agent import AdaptiveAgent

agent = AdaptiveAgent()

# 测试 1: 简单计算
task1 = agent.process("计算 2 + 2")
assert task1.status.value == "success"

# 测试 2: 数据处理
task2 = agent.process("创建一个 CSV 并分析数据")
assert len(task2.steps) > 0

# 测试 3: 错误处理
task3 = agent.process("执行有意的错误")
assert task3.status.value in ["failed", "partial"]

print("✅ 所有测试通过")
```

---

## 🚨 常见问题

### Q1: 系统如何自动安装包？
A: 当检测到缺失的依赖时，执行引擎调用 `pip install` 自动安装。

### Q2: 可以添加自定义工具吗？
A: 是的！使用 `/api/agent/register-tool` 端点或 Python API。

### Q3: 流式响应有超时吗？
A: 默认流式连接保持 300 秒，可通过配置修改。

### Q4: 支持的最大并发请求数？
A: 默认 10 个，取决于系统资源和配置。

### Q5: 如何持久化任务结果？
A: 调用 `task.to_dict()` 序列化为 JSON，存储到数据库或文件。

---

## 📈 使用统计

**测试覆盖率**: 7/7 核心功能 ✅  
**内置工具数**: 6 个 ✅  
**API 端点数**: 7 个 ✅  
**事件类型**: 8 种 ✅  
**支持任务类型**: 9 种 ✅  

---

## 🔄 后续规划

### Phase 2 (短期)
- [ ] 前端仪表板开发
- [ ] 数据库持久化
- [ ] 任务调度和定时执行
- [ ] 长期任务断点续传

### Phase 3 (中期)
- [ ] 扩展工具库（PDF、视频、音频）
- [ ] 分布式执行支持
- [ ] 性能优化和缓存
- [ ] 用户权限管理

### Phase 4 (长期)
- [ ] 机器学习辅助任务分类
- [ ] 自适应学习系统
- [ ] 多模型支持切换
- [ ] 第三方插件市场

---

## 📞 技术支持

### 获取帮助
1. 查看 [ADAPTIVE_AGENT_GUIDE.md](ADAPTIVE_AGENT_GUIDE.md) 详细文档
2. 运行 `test_adaptive_agent_v2.py` 验证功能
3. 检查日志记录获取错误信息
4. 提交问题报告（如适用）

### 调试技巧
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 追踪事件流
def debug_callback(event_type, data):
    print(f"[DEBUG] {event_type}: {data}")

task = agent.process(request, callback=debug_callback)
```

---

## 📝 版本信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 发布日期 | 2026-02-12 |
| 线代码 | 830+ LOC |
| Python 版本 | 3.8+ |
| 依赖库 | Flask, pandas, PIL, requests, beautifulsoup4 |
| 许可证 | MIT |

---

**祝您使用愉快！🚀**

有任何问题，请参考详细指南或运行测试套件。
