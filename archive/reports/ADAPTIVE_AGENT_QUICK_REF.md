# 🤖 Adaptive Agent - 快速参考

## ⚡ 30秒快速开始

### 1️⃣ 验证系统
```bash
python test_adaptive_agent_v2.py
# 预期: 🎉 所有功能验证通过! (7/7)
```

### 2️⃣ Python 代码
```python
from web.adaptive_agent import AdaptiveAgent

agent = AdaptiveAgent()
task = agent.process("你的请求")
print(f"状态: {task.status.value}")
```

### 3️⃣ REST API
```bash
curl -X POST http://localhost:5000/api/agent/process \
  -H "Content-Type: application/json" \
  -d '{"request": "你的请求"}'
```

---

## 📊 核心数据一览

| 组件 | 详情 |
|------|------|
| **位置** | `web/adaptive_agent.py` + `web/adaptive_agent_api.py` |
| **大小** | 830+ 行代码 |
| **工具数** | 6 个内置 + 可扩展 |
| **任务类型** | 9 种（代码、数据、文件、网页、图像、数学、文本、系统、未知） |
| **API 端点** | 7 个（工具、处理、历史、分析、状态、流式、注册） |
| **事件类型** | 8 种（开始、步骤、安装、完成、错误、恢复、最终、完全结束） |

---

## 🎯 使用场景速查

### 场景 A: 代码生成
```python
task = agent.process("写一个快速排序函数")
# → task.status = "success"
# → 自动使用 python_exec 工具
```

### 场景 B: 数据处理
```python
task = agent.process("读取 CSV 并计算均值")
# → 自动安装 pandas/numpy
# → 使用 data_process 工具
# → 返回处理结果
```

### 场景 C: 文件转换
```python
task = agent.process("把 PNG 转为 JPG")
# → 自动安装 pillow
# → 使用 image_proc 工具
# → 保存转换结果
```

### 场景 D: 网页爬取
```python
task = agent.process("爬取网站数据: https://...")
# → 自动安装 requests/beautifulsoup4
# → 使用 network_ops 工具
# → 返回解析数据
```

### 场景 E: 流式监听
```javascript
// 实时获取执行进度
const response = await fetch('/api/agent/process-stream', {
  method: 'POST',
  body: JSON.stringify({ request: "..." })
});

response.body.getReader().read()
// → "data: {type: 'task_started', ...}"
// → "data: {type: 'step_completed', ...}"
// → "data: {type: 'task_final', ...}"
```

---

## 🔧 核心 API

### 处理请求
```python
# 同步处理
task = agent.process(
    request="用户请求",
    context={"key": "value"},
    callback=lambda type, data: print(f"{type}: {data}")
)

# 检查结果
if task.status.value == "success":
    print("✅ 成功")
    for step in task.steps:
        print(f"  {step.description}: {step.status.value}")
else:
    print(f"❌ 失败: {task.errors}")
```

### 任务分析（仅分析，不执行）
```python
analyzer = TaskAnalyzer()
task = analyzer.analyze("用户请求")
print(f"类型: {task.task_type.value}")
print(f"步骤: {len(task.steps)}")
```

### 获取工具列表
```python
registry = ToolRegistry()
tools = registry.list_tools()
for tool_id, tool_def in tools.items():
    print(f"{tool_id}: {tool_def['description']}")
```

### 事件监听
```python
def on_event(event_type, data):
    if event_type == "task_started":
        print(f"🚀 {data['request']}")
    elif event_type == "step_completed":
        print(f"✅ 步骤 {data['step_id']}")
    elif event_type == "task_completed":
        print(f"🎉 完成! 耗时 {data['duration']:.2f}s")

task = agent.process(request, callback=on_event)
```

---

## 📡 REST API 速查

| 方法 | 端点 | 用途 |
|------|------|------|
| **GET** | `/api/agent/tools` | 列出所有工具 |
| **POST** | `/api/agent/process` | 同步处理请求 |
| **POST** | `/api/agent/process-stream` | 流式处理（SSE） |
| **POST** | `/api/agent/analyze` | 仅分析，不执行 |
| **GET** | `/api/agent/history` | 获取执行历史 |
| **GET** | `/api/agent/status` | 获取 Agent 状态 |
| **POST** | `/api/agent/register-tool` | 注册自定义工具 |

---

## 🛠 工具选择速查

| 任务类型 | 关键词示例 | 自动工具 | 依赖包 |
|--------|---------|---------|-------|
| 代码生成 | 代码、脚本、写 | python_exec | - |
| 数据处理 | 数据、CSV、Excel | data_process | pandas, numpy |
| 文件转换 | 转换、导出、格式 | file_ops | - |
| 网页爬取 | 爬取、URL、网站 | network_ops | requests, bs4 |
| 图像处理 | 图片、图像、缩放 | image_proc | pillow |
| 数学计算 | 计算、求解、公式 | python_exec | sympy |
| 文本处理 | 文本、提取、NLP | 文本工具 | nltk, spacy |
| 系统操作 | 打开、运行、启动 | 系统命令 | - |

---

## ⚙️ 配置速查

```python
# 创建 Agent（所有参数可选）
agent = AdaptiveAgent(
    gemini_client=my_client,      # AI 辅助分析（可选）
    max_retries=3,                # 失败重试次数
    timeout=300                   # 任务超时（秒）
)

# 处理请求（所有参数可选）
task = agent.process(
    request="必需: 用户请求",
    context={...},                # 可选: 运行上下文
    callback=func                 # 可选: 事件回调
)
```

---

## 🧪 快速测试

```bash
# 完整功能测试
python test_adaptive_agent_v2.py

# 预期输出
# ✅ 任务分析器
# ✅ 工具注册表
# ✅ Agent 初始化
# ✅ 任务分析
# ✅ 事件系统
# ✅ 任务序列化
# ✅ 上下文系统
# 🎉 所有功能验证通过!
```

---

## 🔍 故障排查

| 问题 | 解决方案 |
|------|--------|
| 包无法安装 | 检查网络、Python 权限、pip 版本 |
| 任务超时 | 增加 `timeout` 参数或分解任务 |
| 找不到工具 | 运行 `GET /api/agent/tools` 查看可用工具 |
| 任务失败 | 检查 `task.errors` 列表，启用日志调试 |
| 流式连接断开 | 检查网络稳定性，增加服务器超时 |

---

## 📚 详细文档

- **功能完整指南**: [ADAPTIVE_AGENT_GUIDE.md](ADAPTIVE_AGENT_GUIDE.md)
- **部署和配置**: [ADAPTIVE_AGENT_DEPLOYMENT.md](ADAPTIVE_AGENT_DEPLOYMENT.md)
- **源代码**: [web/adaptive_agent.py](web/adaptive_agent.py)
- **API 源代码**: [web/adaptive_agent_api.py](web/adaptive_agent_api.py)

---

## 🎓 学习路径

**初级** (15分钟)
1. 运行 `test_adaptive_agent_v2.py` ✅
2. 调用一个简单的 REST API
3. 查看返回结果

**中级** (1小时)
4. 用 Python 集成 Agent
5. 监听事件回调
6. 串联多个任务

**高级** (1天)
7. 创建自定义工具
8. 优化任务性能
9. 建立监控和日志

---

**版本**: 1.0.0 | **状态**: ✅ 生产就绪 | **更新**: 2026-02-12
