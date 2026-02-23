# 🤖 Koto 自适应 Agent 系统 - 使用指南

## 概述

Koto 自适应 Agent 系统是一个智能任务处理框架，能够：

✅ **自动任务理解** - 理解用户自然语言请求  
✅ **智能任务拆分** - 将复杂任务分解为可执行的步骤  
✅ **动态工具调度** - 根据任务需求自动选择和调用适当的工具  
✅ **自动依赖管理** - 自动检测和安装缺失的 Python 包  
✅ **错误恢复** - 智能处理错误并尝试恢复  
✅ **流式反馈** - 支持实时进度反馈

---

## 架构设计

```
┌─────────────────────────────────────────┐
│         用户请求 (自然语言)             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      任务分析器 (TaskAnalyzer)          │
│  - 任务分类 (9个任务类型)               │
│  - 任务拆分 (AI或启发式)                │
│  - 依赖识别                              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│    执行计划 (多个任务步骤)              │
│  - 步骤序列                              │
│  - 所需工具                              │
│  - 所需包                                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│    执行引擎 (ExecutionEngine)           │
│  - 依赖管理 (自动安装包)                │
│  - 循序执行                              │
│  - 错误处理和恢复                        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      工具注册表 (ToolRegistry)          │
│  - python_exec (代码执行)               │
│  - file_ops (文件操作)                  │
│  - data_process (数据处理)              │
│  - image_proc (图像处理)                │
│  - network_ops (网络操作)               │
│  - package_mgmt (包管理)                │
└─────────────────────────────────────────┘
```

---

## 支持的任务类型

| 类型 | 关键词 | 工具 | 自动依赖 |
|------|--------|------|---------|
| 代码生成 | 代码、脚本、写 | python_exec | - |
| 数据处理 | 数据、CSV、Excel | data_process | pandas, numpy |
| 文件转换 | 转换、导出、格式 | file_ops | 特定转换库 |
| 网页爬取 | 爬取、网页、URL | network_ops | requests, bs4 |
| 图像处理 | 图片、图像、缩放 | image_proc | pillow |
| 数学计算 | 计算、求解、方程 | python_exec | sympy |
| 文本处理 | 文本、提取、NLP | text_proc | nltk, spacy |
| 系统操作 | 打开、运行、启动 | 系统命令 | - |

---

## REST API 文档

### 1. 获取可用工具

**请求:**
```bash
GET /api/agent/tools
```

**响应:**
```json
{
  "success": true,
  "tools": {
    "python_exec": {
      "name": "python_exec",
      "description": "执行 Python 代码片段",
      "dependencies": [],
      "file_handler": false,
      "can_chain": true
    },
    ...
  },
  "count": 6
}
```

### 2. 处理请求（同步）

**请求:**
```bash
POST /api/agent/process
Content-Type: application/json

{
  "request": "帮我读取 data.csv 并计算平均值",
  "context": {
    "working_dir": "/path/to/dir"
  }
}
```

**响应:**
```json
{
  "success": true,
  "task": {
    "task_id": "task_1707639600000",
    "user_request": "帮我读取 data.csv 并计算平均值",
    "task_type": "data_processing",
    "status": "success",
    "steps": [
      {
        "step_id": 1,
        "description": "加载数据文件",
        "status": "success",
        "duration": 0.234,
        "result": "..."
      },
      ...
    ],
    "duration": 2.456,
    "errors": []
  }
}
```

### 3. 处理请求（流式 SSE）

**请求:**
```bash
POST /api/agent/process-stream
Content-Type: application/json

{
  "request": "写一个计算斐波那契数列的函数",
  "session_id": "user_123"
}
```

**响应（流式事件）:**
```
data: {"type": "task_started", "data": {...}}

data: {"type": "step_started", "data": {"step_id": 1, "description": "..."}

data: {"type": "installing_packages", "data": {"packages": [...]}}

data: {"type": "step_completed", "data": {"step_id": 1, "status": "success"}}

data: {"type": "task_final", "data": {...}}
```

### 4. 仅分析任务（不执行）

**请求:**
```bash
POST /api/agent/analyze
Content-Type: application/json

{
  "request": "帮我转换 image.png 为 JPG 格式"
}
```

**响应:**
```json
{
  "success": true,
  "task_type": "file_conversion",
  "description": "转换图像文件格式",
  "steps": [
    {
      "step_id": 1,
      "description": "识别文件类型",
      "action": "identify"
    },
    ...
  ],
  "required_packages": ["pillow"]
}
```

### 5. 获取任务历史

**请求:**
```bash
GET /api/agent/history
```

**响应:**
```json
{
  "success": true,
  "history": [
    {
      "task_id": "task_1707639600000",
      "user_request": "...",
      "status": "success",
      "duration": 2.456
    },
    ...
  ],
  "count": 5
}
```

### 6. 获取 Agent 状态

**请求:**
```bash
GET /api/agent/status
```

**响应:**
```json
{
  "success": true,
  "agent": {
    "initialized": true,
    "tools_available": 6,
    "tasks_completed": 5
  }
}
```

---

## 使用示例

### Python 脚本集成

```python
from adaptive_agent import AdaptiveAgent

# 创建 Agent
agent = AdaptiveAgent(gemini_client=my_client)

# 定义事件处理器
def on_event(event_type, data):
    if event_type == "task_started":
        print(f"任务开始: {data['request']}")
    elif event_type == "step_completed":
        print(f"步骤 {data['step_id']} 完成，耗时 {data['duration']:.2f}s")
    elif event_type == "installing_packages":
        print(f"安装包: {', '.join(data['packages'])}")

# 处理请求
task = agent.process(
    "帮我分析 sales_data.csv 并生成统计报告",
    context={"output_dir": "./reports"},
    callback=on_event
)

# 检查结果
print(f"任务状态: {task.status.value}")
print(f"耗时: {task.duration:.2f}s")
if task.errors:
    print(f"错误: {', '.join(task.errors)}")
```

### JavaScript/前端集成

```javascript
// 方案 1: 同步请求
async function processRequest(request) {
  const response = await fetch('/api/agent/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request })
  });
  
  const data = await response.json();
  if (data.success) {
    console.log(`任务完成，耗时 ${data.task.duration}s`);
    return data.task;
  }
}

// 方案 2: 流式请求
async function processRequestStream(request, onEvent) {
  const response = await fetch('/api/agent/process-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      request,
      session_id: `user_${Date.now()}`
    })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    for (let i = 0; i < lines.length - 1; i++) {
      if (lines[i].startsWith('data: ')) {
        const event = JSON.parse(lines[i].substring(6));
        onEvent(event);
      }
    }
    
    buffer = lines[lines.length - 1];
  }
}

// 使用
processRequestStream("写一个快速排序算法", (event) => {
  if (event.type === 'task_started') {
    console.log('任务开始处理...');
  } else if (event.type === 'installing_packages') {
    console.log(`正在安装包: ${event.data.packages.join(', ')}`);
  } else if (event.type === 'step_completed') {
    console.log(`步骤 ${event.data.step_id} 完成`);
  } else if (event.type === 'task_final') {
    console.log('任务完成!');
    console.log(event.data);
  }
});
```

---

## 高级功能

### 1. 自定义工具注册

```python
from adaptive_agent import ToolRegistry, ToolDefinition, Dependency

registry = ToolRegistry()

# 定义工具
def my_custom_tool(input_data):
    return {"success": True, "result": "处理结果"}

# 注册工具
registry.register_tool(
    "my_tool",
    my_custom_tool,
    ToolDefinition(
        name="my_tool",
        description="我的自定义工具",
        dependencies=[
            Dependency("numpy", "np")
        ],
        can_chain=True
    )
)
```

### 2. 任务上下文持久化

```python
# 保存任务状态
task_state = task.to_dict()
with open(f"task_{task.task_id}.json", 'w') as f:
    json.dump(task_state, f)

# 恢复任务
with open(f"task_{task.task_id}.json") as f:
    saved_state = json.load(f)
```

### 3. 条件执行和重试

```python
class SmartExecutor(ExecutionEngine):
    def _try_recover(self, step, task):
        """智能恢复策略"""
        if "timeout" in step.error:
            # 增加超时并重试
            return True
        elif "missing_dependency" in step.error:
            # 自动安装并重试
            return True
        else:
            return False
```

---

## 最佳实践

### 1. 错误处理

```python
try:
    task = agent.process(request)
    if task.status != ExecutionStatus.SUCCESS:
        print(f"任务失败: {task.errors}")
except Exception as e:
    print(f"异常: {e}")
```

### 2. 超时管理

```python
task = agent.process(
    request,
    context={"timeout": 300}  # 5分钟超时
)
```

### 3. 进度跟踪

```python
progress_updates = []

def track_progress(event_type, data):
    if event_type == "step_completed":
        progress = (
            data['step_id'] / total_steps * 100
        )
        progress_updates.append(progress)

task = agent.process(request, callback=track_progress)
```

---

## 常见问题

**Q: Agent 能处理哪些类型的问题？**
A: 任何涉及数据处理、代码生成、文件转换、网络操作、图像处理的问题。只要能用 Python 实现，Agent 都能处理。

**Q: 包无法自动安装怎么办？**
A: 检查网络连接，或手动运行 `pip install package_name`。

**Q: 如何添加新的工具类型？**
A: 继承 ToolRegistry，实现新的工具函数，注册即可。

**Q: 支持链式调用吗？**
A: 支持！设置 `can_chain=True`，Agent 会自动链接多个工具。

---

## 性能优化

- **缓存**: Agent 缓存已安装的包
- **并行**: 可独立的步骤可以并行执行
- **流式**: 支持流式反馈降低延迟
- **重用**: 工具实例可重用

---

## 扩展方向

未来可能的扩展：
- 🔄 分布式执行（多机协作）
- 🧠 学习机制（记住最佳实践）
- 📊 可视化界面（任务流程图）
- 🔌 插件系统（第三方工具）
- 💾 持久化存储（任务日志）

---

**版本**: 1.0.0  
**最后更新**: 2026-02-12  
**维护者**: Koto Team
