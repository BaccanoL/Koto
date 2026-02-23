# DOC_ANNOTATE 前端集成指南

## 快速上手

### SSE 事件处理

DOC_ANNOTATE 任务通过 `/api/chat/stream` 端点返回 SSE（Server-Sent Events）流，包含多个阶段的进度更新。

---

## 事件类型详解

### 1️⃣ `progress` 事件 - 进度更新

**发送频率**: 每个处理阶段发送多次

**数据结构**:
```json
{
  "type": "progress",
  "message": "📖 正在读取文档...",
  "detail": "电影时间的计算解析.docx",
  "progress": 5
}
```

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `message` | string | 主进度显示 | "📖 正在读取文档..." |
| `detail` | string | 详细说明（可选） | "电影时间的计算解析.docx" |
| `progress` | number | 进度百分比 (0-100) | 5, 25, 50, 85 |

**前端显示建议**:
```javascript
// 更新进度条
progressBar.value = event.progress;
progressBar.max = 100;

// 更新状态文字
statusText.textContent = event.message;
if (event.detail) {
  detailText.textContent = event.detail;
}
```

---

### 2️⃣ `info` 事件 - 任务信息

**发送时机**: 处理开始时，显示任务基本信息

**数据结构**:
```json
{
  "type": "info",
  "message": "📋 【任务信息】\n- 模型: gemini-3-pro-preview\n- 需求: 把所有不合适的翻译标注改善\n- 文档: 电影时间的计算解析.docx"
}
```

**前端显示**:
```javascript
// 显示为额外的信息框
infoBox.textContent = event.message;
infoBox.style.display = 'block';
```

---

### 3️⃣ `token` 事件 - 最终报告

**发送时机**: 处理完成时，包含详细的处理结果

**数据结构**:
```json
{
  "type": "token",
  "content": "✅ **文档修改完成！**\n\n📊 **修改统计**：\n- 找到并应用: **23** 处修改\n..."
}
```

**前端显示** (Markdown 渲染):
```javascript
// 渲染为 Markdown（需要 markdown-it 或 marked）
import marked from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';

outputArea.innerHTML = marked(event.content);
```

---

### 4️⃣ `done` 事件 - 完成

**发送时机**: 流式处理结束

**数据结构**:
```json
{
  "type": "done",
  "images": [],
  "saved_files": ["workspace/documents/电影时间的计算解析_revised.docx"],
  "total_time": 28.5
}
```

| 字段 | 说明 |
|------|------|
| `saved_files` | 生成的输出文件路径列表 |
| `total_time` | 总耗时（秒） |

**前端处理**:
```javascript
if (event.saved_files && event.saved_files.length > 0) {
  downloadBtn.href = event.saved_files[0];
  downloadBtn.style.display = 'inline-block';
}
console.log(`处理耗时: ${event.total_time}s`);
```

---

### 5️⃣ `error` 事件 - 错误信息

**发送时机**: 处理失败时

**数据结构**:
```json
{
  "type": "error",
  "message": "❌ 处理失败: 文档格式不正确"
}
```

**前端处理**:
```javascript
errorAlert.textContent = event.message;
errorAlert.style.display = 'block';
errorAlert.className = 'alert alert-danger';
```

---

## 前端实现示例

### Vue 3 组件示例

```vue
<template>
  <div class="doc-annotate-container">
    <!-- 进度条 -->
    <div v-if="isProcessing" class="progress-section">
      <div class="percentage">{{ progress }}%</div>
      <progress :value="progress" max="100"></progress>
      <div class="status-message">{{ currentMessage }}</div>
      <div v-if="currentDetail" class="status-detail">{{ currentDetail }}</div>
    </div>

    <!-- 任务信息 -->
    <div v-if="taskInfo" class="info-box">
      <pre>{{ taskInfo }}</pre>
    </div>

    <!-- 最终报告 -->
    <div v-if="finalReport" class="report-section">
      <div class="markdown-content" v-html="markdownHtml"></div>
    </div>

    <!-- 错误信息 -->
    <div v-if="errorMessage" class="alert alert-danger">
      {{ errorMessage }}
    </div>

    <!-- 下载按钮 -->
    <div v-if="outputFiles.length > 0" class="download-section">
      <a v-for="file in outputFiles" 
         :key="file"
         :href="file"
         class="btn btn-primary"
         download>
        📥 下载: {{ getFileName(file) }}
      </a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import marked from 'marked'

const progress = ref(0)
const currentMessage = ref('')
const currentDetail = ref('')
const taskInfo = ref('')
const finalReport = ref('')
const errorMessage = ref('')
const outputFiles = ref([])
const isProcessing = ref(false)

// 渲染 Markdown
const markdownHtml = computed(() => {
  return marked(finalReport.value)
})

// 连接 SSE 流
function connectSSE(sessionName, userMessage) {
  isProcessing.value = true
  
  const eventSource = new EventSource(
    `/api/chat/stream?session=${sessionName}&message=${encodeURIComponent(userMessage)}`
  )
  
  eventSource.addEventListener('message', (e) => {
    const data = JSON.parse(e.data)
    
    switch(data.type) {
      case 'progress':
        progress.value = data.progress || 0
        currentMessage.value = data.message || ''
        currentDetail.value = data.detail || ''
        break
        
      case 'info':
        taskInfo.value = data.message
        break
        
      case 'token':
        finalReport.value = data.content || ''
        break
        
      case 'done':
        outputFiles.value = data.saved_files || []
        isProcessing.value = false
        eventSource.close()
        break
        
      case 'error':
        errorMessage.value = data.message
        isProcessing.value = false
        eventSource.close()
        break
    }
  })
  
  eventSource.onerror = () => {
    errorMessage.value = '连接中断'
    isProcessing.value = false
    eventSource.close()
  }
}

function getFileName(filePath) {
  return filePath.split('/').pop()
}
</script>

<style scoped>
.progress-section {
  margin: 20px 0;
}

.percentage {
  font-weight: bold;
  margin-bottom: 10px;
}

progress {
  width: 100%;
  height: 24px;
  border-radius: 4px;
}

.status-message {
  margin-top: 10px;
  font-weight: bold;
}

.status-detail {
  color: #666;
  font-size: 0.9em;
  margin-top: 5px;
}

.info-box {
  background: #f0f7ff;
  border: 1px solid #cce5ff;
  padding: 12px;
  margin: 15px 0;
  border-radius: 4px;
  font-size: 0.85em;
}

.report-section {
  margin-top: 20px;
  padding: 15px;
  background: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.markdown-content {
  line-height: 1.6;
}

.markdown-content strong {
  color: #333;
}

.download-section {
  margin-top: 15px;
}

.download-section a {
  display: inline-block;
  margin-right: 10px;
}
</style>
```

---

### 原生 JavaScript 示例

```javascript
function handleDocAnnotateStream(sessionName, userMessage) {
  const container = document.getElementById('doc-annotate-container')
  const progressBar = container.querySelector('.progress-bar')
  const statusText = container.querySelector('.status-text')
  const reportArea = container.querySelector('.report-area')
  
  const eventSource = new EventSource(
    `/api/chat/stream?session=${sessionName}&message=${encodeURIComponent(userMessage)}`
  )
  
  eventSource.addEventListener('text/event-stream', function(event) {
    if (!event.data.startsWith('data: ')) return
    
    const data = JSON.parse(event.data.substring(6))
    
    // 更新进度条
    if (data.type === 'progress') {
      progressBar.value = data.progress || 0
      statusText.textContent = `${data.message} ${data.detail ? `(${data.detail})` : ''}`
    }
    
    // 显示最终报告
    if (data.type === 'token') {
      // 需要导入 markdown 库
      reportArea.innerHTML = marked.parse(data.content)
    }
    
    // 完成处理
    if (data.type === 'done') {
      if (data.saved_files && data.saved_files.length > 0) {
        const downloadBtn = document.createElement('a')
        downloadBtn.href = data.saved_files[0]
        downloadBtn.textContent = '📥 下载文档'
        downloadBtn.className = 'btn btn-primary'
        downloadBtn.download = ''
        reportArea.appendChild(downloadBtn)
      }
      eventSource.close()
    }
  })
}
```

---

## 样式参考

### 进度显示样式

```html
<div class="doc-progress">
  <div class="progress-bar-container">
    <div class="progress-percentage">25%</div>
    <progress value="25" max="100"></progress>
  </div>
  <div class="progress-details">
    <div class="stage-item completed">
      <span class="stage-check">✓</span>
      <span class="stage-name">读取文档</span>
      <span class="stage-detail">50段 | 8500字</span>
    </div>
    <div class="stage-item active">
      <span class="stage-spinner">⟳</span>
      <span class="stage-name">分析文档</span>
      <span class="stage-detail">正在处理...</span>
    </div>
    <div class="stage-item pending">
      <span class="stage-icon">•</span>
      <span class="stage-name">应用修改</span>
    </div>
  </div>
</div>
```

```css
.doc-progress {
  max-width: 600px;
  margin: 20px auto;
}

.progress-bar-container {
  position: relative;
  margin-bottom: 20px;
}

.progress-percentage {
  text-align: center;
  font-weight: bold;
  font-size: 18px;
  margin-bottom: 10px;
}

progress {
  width: 100%;
  height: 30px;
  border-radius: 15px;
  border: none;
  background: #e0e0e0;
  overflow: hidden;
}

progress::-webkit-progress-bar {
  background: #e0e0e0;
}

progress::-webkit-progress-value {
  background: linear-gradient(90deg, #4CAF50, #45a049);
  transition: width 0.3s;
}

.stage-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin: 8px 0;
  border-radius: 4px;
  background: #f5f5f5;
}

.stage-item.completed {
  background: #e8f5e9;
  color: #2e7d32;
}

.stage-item.active {
  background: #fff3e0;
  color: #e65100;
}

.stage-item.pending {
  background: #eeeeee;
  color: #999;
}

.stage-check,
.stage-spinner,
.stage-icon {
  margin-right: 12px;
  font-weight: bold;
}

.stage-name {
  flex: 1;
  font-weight: 500;
}

.stage-detail {
  font-size: 0.85em;
  color: inherit;
  opacity: 0.8;
}
```

---

## 常见问题

### Q1: 为什么没有收到 `done` 事件？
A: 检查网络连接，确保客户端没有在处理完成前断开连接。

### Q2: 如何显示实时修改建议？
A: 可以在 `token` 事件中包含修改摘要，或添加新的事件类型 `changes` 来逐个返回修改。

### Q3: 能否中断正在处理的任务？
A: 前端可以关闭 EventSource 连接来中断流，后端应支持中断标志。

---

## 部署清单

- [ ] 前端能正确解析 SSE 事件格式
- [ ] 进度条显示正常
- [ ] Markdown 内容渲染正确
- [ ] 下载链接可用
- [ ] 错误提示清晰
- [ ] 测试各个阶段的事件
- [ ] 测试错误边界情况

---

## 参考资源

- [MDN: Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [marked.js](https://marked.js.org/)
- [SSE 客户端示例](https://html.spec.whatwg.org/multipage/server-sent-events.html)
