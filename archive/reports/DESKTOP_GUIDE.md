# 📱 Koto Desktop - 独立桌面应用指南

> 一个专业的、自适应的、完全独立的桌面应用程序  
> 类似 VSCode、微信一样的原生应用体验

## ✨ 特点

- ✅ **完全独立** - 无需 Flask、无需端口映射
- ✅ **专业 UI** - 类似 VSCode 和微信的现代界面
- ✅ **一键启动** - 无需配置，开箱即用
- ✅ **智能自适应** - 集成 Adaptive Agent 系统
- ✅ **无依赖管理** - 所有依赖自动处理
- ✅ **跨越隔离** - 直接访问系统资源

---

## 🚀 快速开始

### 方式 A: 直接运行 (推荐用于开发)

```bash
# 双击运行
python launch_desktop.py

# 或使用批处理脚本
run_desktop.bat
```

### 方式 B: 编译成独立 EXE (推荐用于分发)

```bash
# 生成完全独立的应用
python build_desktop_app.py
```

生成的应用会自动复制到桌面，无需 Python 即可运行。

### 方式 C: 从源代码启动

```bash
cd Koto
python koto_desktop.py
```

---

## 📂 文件结构

```
Koto/
├── koto_desktop.py              # 主应用程序 (PyQt6/PySide6)
├── run_desktop.bat              # Windows 启动脚本
├── launch_desktop.py            # Python 启动器
├── build_desktop_app.py         # PyInstaller 打包工具
├── DESKTOP_GUIDE.md             # 本文档
├── web/                         # Web 组件和 API
├── config/                      # 配置文件
├── assets/                      # 应用资源
├── models/                      # AI 模型
└── logs/                        # 日志文件
```

---

## 🎨 应用界面

### 主窗口布局

```
┌─────────────────────────────────────────────┐
│ Koto - 智能桌面助手  [−][□][×]             │
├──────────────┬──────────────────────────────┤
│ KOTO         │                              │
│ 🤖 任务处理  │    任务处理界面              │
│ 📄 文档处理  │  (主要工作区)                │
│ 💬 AI 助手   │                              │
│ ⚙️ 设置      │                              │
│ ℹ️ 关于      │                              │
│              │                              │
│ v1.0.0       └──────────────────────────────┘
└─────────────────────────────────────────────┘
```

### 功能面板

#### 1️⃣ 任务处理 (🤖)
- 输入自然语言任务
- 自适应 Agent 自动分析执行
- 实时查看执行结果
- 支持复杂的多步骤流程

**示例任务:**
```
- 创建一个 Word 文档，包含今日待办任务
- 发送邮件给 team@example.com
- 打开微信并发送特定消息
- 生成一个 PowerPoint 演示文稿
```

#### 2️⃣ 文档处理 (📄)
- 创建 Word 文档
- 生成 PowerPoint 演示文稿
- 创建 Excel 表格
- 分析文档内容
- 编辑现有文档
- 导出为其他格式

#### 3️⃣ AI 助手 (💬)
- 实时聊天交互
- 自然语言理解
- 学习用户习惯
- 个性化建议

#### 4️⃣ 设置 (⚙️)
- 主题选择
- API 配置
- 快捷键管理
- 启动选项

#### 5️⃣ 关于 (ℹ️)
- 版本信息
- 功能说明
- 快速开始指南
- 相关资源链接

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+N` | 新建任务 |
| `Ctrl+,` | 打开设置 |
| `Ctrl+Q` | 退出应用 |
| `Ctrl+Enter` | 在任务面板提交任务 |
| `Ctrl+I` | 打开 AI 助手 |
| `Ctrl+D` | 打开文档处理 |

---

## 🔧 配置

### 应用配置文件位置

```
config/
├── user_settings.json      # 用户偏好设置
├── gemini_config.env       # API 配置
└── app_config.json         # 应用配置
```

### 修改应用设置

编辑 `config/user_settings.json`:

```json
{
  "theme": "dark",
  "language": "zh-CN",
  "auto_save": true,
  "api_key": "your-api-key",
  "startup_panel": "task"
}
```

---

## 📦 编译和分发

### 编译为独立 EXE

```bash
python build_desktop_app.py
```

**输出位置:**
```
desktop_apps/
├── Koto_v1.0.0_Standalone.zip    # 分发包
├── BUILD_SUMMARY.json             # 构建信息
└── README.txt                      # 快速开始指南
```

### 分发方式

1. **ZIP 包分发**: 最简单，只需分享 ZIP 文件
2. **EXE 安装程序**: 传统安装体验 (需要 NSIS)
3. **U 盘启动**: 解压到 U 盘，支持离线运行
4. **网络部署**: 放在网络共享文件夹

### 系统要求

| 要求 | 规格 |
|------|------|
| 操作系统 | Windows 7 SP1 或更高 |
| 内存 | 1 GB RAM (推荐 4 GB+) |
| 磁盘 | 500 MB (编译版需要 300-500 MB) |
| 网络 | 部分功能需要互联网 |

---

## 🐛 故障排查

### 问题：应用启动缓慢

**原因**: 首次启动需要初始化

**解决**:
- 首次启动是正常的，可能需要 10-30 秒
- 后续启动会快得多
- 检查日志文件了解详细信息

### 问题：Agent 功能不可用

**原因**: API 未配置或网络问题

**解决**:
1. 检查 `config/gemini_config.env`
2. 确保 API Key 有效
3. 检查网络连接
4. 查看日志文件: `logs/`

### 问题：文档处理失败

**原因**: 依赖库未安装

**解决**:
```bash
pip install python-docx python-pptx openpyxl
```

### 问题：编译失败

**原因**: PyInstaller 问题

**解决**:
```bash
# 清除之前的构建
rmdir /s dist build

# 重新安装 PyInstaller
pip install pyinstaller --upgrade

# 重新编译
python build_desktop_app.py
```

## 日志查看

应用日志保存在 `logs/` 目录:

```bash
# 查看最新日志
logs/desktop_*.log
```

日志包含:
- 应用启动信息
- 错误信息
- Agent 执行日志
- API 调用记录

---

## 🔐 安全性和隐私

- ✅ 所有处理在本地进行
- ✅ 敏感信息不上传
- ✅ 配置文件加密存储
- ✅ 支持离线模式

---

## 📚 相关文档

- [INSTALLER_GUIDE.md](./INSTALLER_GUIDE.md) - 完整安装指南
- [README.md](./README.md) - 项目说明
- [adaptive_agent_guide.md](./docs/ADAPTIVE_AGENT_GUIDE.md) - Agent 系统说明

---

## 🚀 开发指南

### 添加新功能

1. 在 `koto_desktop.py` 中添加新的面板类
2. 继承 `QWidget` 基类
3. 实现 `setup_ui()` 和功能方法
4. 注册到主窗口导航栏

### 集成外部工具

```python
# 在面板中集成工具
from web.some_module import SomeFunction

class MyCustomPanel(QWidget):
    def handle_task(self, input_data):
        result = SomeFunction(input_data)
        return result
```

### 自定义主题

编辑 `apply_stylesheet()` 方法:

```python
stylesheet = """
    QMainWindow {
        background-color: #ffffff;
    }
    /* ... 更多样式 */
"""
```

---

## 💡 最佳实践

### 性能优化

1. **延迟加载**: 在需要时才导入重型库
2. **缓存**: 缓存常用数据
3. **线程**: 将长操作放在后台线程
4. **监控**: 定期检查日志和性能

### 用户体验

1. **反馈**: 提供清晰的操作反馈
2. **快捷键**: 支持常用快捷键
3. **样式**: 保持一致的视觉设计
4. **帮助**: 提供完整的帮助文档

---

## 📞 支持

遇到问题？

1. **查看日志**: `logs/desktop_*.log`
2. **查阅文档**: 本指南和相关文档
3. **检查设置**: `config/` 配置文件
4. **重新启动**: 关闭应用，重新启动

---

## 🎉 完成！

您现在拥有一个专业的、功能强大的桌面应用程序！

**下一步:**
1. 运行 `run_desktop.bat` 或 `python launch_desktop.py`
2. 探索应用功能
3. 根据需要配置设置
4. 使用 `build_desktop_app.py` 编译和分发

---

**版本**: 1.0.0  
**最后更新**: 2026-02-12  
**作者**: Koto Team
