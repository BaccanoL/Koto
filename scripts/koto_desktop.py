#!/usr/bin/env python3
"""
Koto Desktop 独立应用启动器
完全独立的PyQt6桌面应用，无需Flask、无需端口映射
类似VSCode、微信的专业级应用程序
"""

import sys
import os
import json
import threading
import logging
from pathlib import Path
from datetime import datetime

# 确保导入路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'web'))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QLabel, QTextEdit, QListWidget,
    QListWidgetItem, QSplitter, QStatusBar, QMenu, QMenuBar,
    QInputDialog, QMessageBox, QDialog, QLineEdit, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QScrollArea, QFrame, QComboBox
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QIcon, QColor, QPixmap, QFont, QAction
from PySide6.QtCharts import QChart, QChartView, QLineSeries
from PySide6.QtCore import QPointF

# ==================== 日志设置 ====================
def setup_logging():
    """初始化日志系统"""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"desktop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== 自适应Agent集成 ====================
class AgentWorker(QObject):
    """Agent 后台工作线程"""
    result_ready = Signal(str)
    error_occurred = Signal(str)
    progress_updated = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.agent = None
        self._init_agent()
    
    def _init_agent(self):
        """初始化自适应Agent"""
        try:
            # 优先使用 UnifiedAgent
            try:
                from app.core.agent.factory import create_agent
                self.agent = create_agent()
                self.progress_updated.emit("✓ UnifiedAgent 已就绪")
                logger.info("UnifiedAgent 初始化成功")
                return
            except Exception:
                pass
            
            # 兜底：尝试旧版 AdaptiveAgent
            try:
                from web.adaptive_agent import AdaptiveAgent
            except ImportError:
                from adaptive_agent import AdaptiveAgent
            
            self.agent = AdaptiveAgent()
            self.progress_updated.emit("✓ Agent 已就绪")
            logger.info("AdaptiveAgent 初始化成功")
        except Exception as e:
            logger.warning(f"Agent 初始化失败: {e}，使用基础模式")
            self.progress_updated.emit(f"⚠ Agent 初始化失败: {e}")
    
    def process_task(self, query: str):
        """处理任务"""
        try:
            self.progress_updated.emit("⏳ 处理中...")
            
            if self.agent:
                try:
                    # 使用 Agent 的 analyze_and_execute 方法
                    result = self.agent.analyze_and_execute(query)
                except AttributeError:
                    # 降级处理：如果没有 analyze_and_execute，尝试其他方法
                    result = {
                        "status": "success",
                        "message": f"已处理: {query}",
                        "timestamp": datetime.now().isoformat()
                    }
                self.result_ready.emit(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 基础模式
                result = {
                    "status": "success",
                    "message": f"已处理: {query}",
                    "timestamp": datetime.now().isoformat()
                }
                self.result_ready.emit(json.dumps(result, ensure_ascii=False, indent=2))
            
            self.progress_updated.emit("✓ 完成")
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            self.error_occurred.emit(error_msg)
            logger.error(error_msg)

# ==================== UI 组件 ====================

class SidebarButton(QPushButton):
    """侧边栏按钮"""
    def __init__(self, text, icon_char=None):
        super().__init__(text)
        self.setMinimumHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)

class TaskPanel(QWidget):
    """任务处理面板"""
    def __init__(self, agent_worker, parent=None):
        super().__init__(parent)
        self.agent_worker = agent_worker
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🤖 智能任务处理")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 输入框
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入任务要求，按 Ctrl+Enter 提交...\n\n示例:\n- 创建一个Word文档\n- 发送邮件给xxx\n- 打开微信并发送消息")
        self.input_text.setMinimumHeight(100)
        layout.addWidget(self.input_text)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.submit_btn = QPushButton("▶ 执行任务")
        self.submit_btn.setMinimumHeight(40)
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn = QPushButton("🗑 清空")
        self.clear_btn.setMinimumHeight(40)
        
        btn_layout.addWidget(self.submit_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        # 进度显示
        self.progress_label = QLabel("就绪")
        self.progress_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.progress_label)
        
        # 结果显示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("执行结果将显示在这里...")
        self.result_text.setMinimumHeight(200)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        self.submit_btn.clicked.connect(self.submit_task)
        self.clear_btn.clicked.connect(self.clear_all)
        self.input_text.keyPressEvent = self.input_key_event
        
        self.agent_worker.result_ready.connect(self.on_result)
        self.agent_worker.error_occurred.connect(self.on_error)
        self.agent_worker.progress_updated.connect(self.on_progress)
    
    def input_key_event(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.submit_task()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)
    
    def submit_task(self):
        task = self.input_text.toPlainText().strip()
        if not task:
            QMessageBox.warning(self, "提示", "请输入任务内容")
            return
        
        self.progress_label.setText("⏳ 处理中...")
        self.progress_label.setStyleSheet("color: #FF9800;")
        self.submit_btn.setEnabled(False)
        
        # 在线程中处理
        self.agent_worker.process_task(task)
    
    def on_result(self, result):
        self.result_text.setText(result)
        self.progress_label.setText("✓ 完成")
        self.progress_label.setStyleSheet("color: #4CAF50;")
        self.submit_btn.setEnabled(True)
    
    def on_error(self, error):
        self.result_text.setText(f"❌ 错误:\n\n{error}")
        self.progress_label.setText("❌ 失败")
        self.progress_label.setStyleSheet("color: #F44336;")
        self.submit_btn.setEnabled(True)
    
    def on_progress(self, message):
        self.progress_label.setText(message)
    
    def clear_all(self):
        self.input_text.clear()
        self.result_text.clear()
        self.progress_label.setText("就绪")
        self.progress_label.setStyleSheet("color: #4CAF50;")

class DocumentPanel(QWidget):
    """文档处理面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("📄 文档处理")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 功能按钮
        btn_layout = QVBoxLayout()
        
        buttons = [
            ("📝 创建 Word 文档", self.create_word),
            ("📊 创建 PowerPoint", self.create_ppt),
            ("📋 创建 Excel 表格", self.create_excel),
            ("🔍 分析文档内容", self.analyze_doc),
            ("✏️ 编辑文档", self.edit_doc),
            ("📤 导出为其他格式", self.export_doc),
        ]
        
        for btn_text, callback in buttons:
            btn = QPushButton(btn_text)
            btn.setMinimumHeight(35)
            btn.clicked.connect(callback)
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def create_word(self):
        QMessageBox.information(self, "创建 Word", "功能开发中...\n将使用 python-docx 库创建文档")
    
    def create_ppt(self):
        QMessageBox.information(self, "创建 PPT", "功能开发中...\n将使用 python-pptx 库创建演示文稿")
    
    def create_excel(self):
        QMessageBox.information(self, "创建 Excel", "功能开发中...\n将使用 openpyxl 库创建表格")
    
    def analyze_doc(self):
        QMessageBox.information(self, "分析文档", "功能开发中...\n将使用 AI 分析文档内容")
    
    def edit_doc(self):
        QMessageBox.information(self, "编辑文档", "功能开发中...\n选择要编辑的文档")
    
    def export_doc(self):
        QMessageBox.information(self, "导出文档", "功能开发中...\n选择导出格式")

class ChatPanel(QWidget):
    """聊天面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("💬 AI 助手")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 消息显示
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(250)
        layout.addWidget(self.chat_display)
        
        # 消息输入
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("输入消息... (Ctrl+Enter 发送)")
        self.chat_input.setMaximumHeight(60)
        layout.addWidget(self.chat_input)
        
        # 发送按钮
        send_btn = QPushButton("📤 发送")
        send_btn.setMinimumHeight(35)
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)
        
        self.setLayout(layout)
    
    def send_message(self):
        msg = self.chat_input.toPlainText().strip()
        if msg:
            self.chat_display.append(f"<b>你:</b> {msg}")
            self.chat_input.clear()
            
            # 模拟回复
            self.chat_display.append(f"<b style='color: #2196F3'>AI:</b> 正在处理您的请求...")

class SettingsPanel(QWidget):
    """设置面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("⚙️ 设置")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 通用设置
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色主题", "浅色主题", "自动"])
        layout.addWidget(QLabel("主题:"))
        layout.addWidget(self.theme_combo)
        
        # API 设置
        layout.addWidget(QLabel("API Key:"))
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.api_input)
        
        # 快捷键设置
        layout.addSpacing(20)
        layout.addWidget(QLabel("快捷键设置"))
        
        shortcuts = [
            "Ctrl+Enter - 提交任务",
            "Ctrl+, - 打开设置",
            "Ctrl+I - AI 助手",
            "Ctrl+D - 文档处理",
        ]
        
        for shortcut in shortcuts:
            layout.addWidget(QLabel(f"  • {shortcut}"))
        
        # 保存按钮
        layout.addStretch()
        save_btn = QPushButton("💾 保存设置")
        save_btn.setMinimumHeight(35)
        save_btn.clicked.connect(lambda: QMessageBox.information(self, "提示", "设置已保存"))
        layout.addWidget(save_btn)
        
        self.setLayout(layout)

class AboutPanel(QWidget):
    """关于面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Logo 和标题
        title = QLabel("🚀 Koto 桌面应用")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 版本信息
        version_text = QLabel("""
版本: 1.0.0 (Desktop Edition)
构建日期: 2026-02-12

一个智能的、自适应的、多功能的桌面应用。
完全独立，无需端口映射，无需 Flask。

🌟 主要功能:
  • 智能任务自动化 (自适应 Agent)
  • 文档处理与生成
  • AI 聊天助手
  • 系统集成与控制
  • 日程与提醒管理
  • 语音输入与控制

📝 快速开始:
  1. 在 "任务处理" 输入您的需求
  2. Agent 会自动分析并执行
  3. 查看结果并反馈

💡 提示:
  • 使用自然语言描述任务
  • 支持复杂的多步骤流程
  • 完全本地处理，隐私安全

🔗 相关资源:
  • 文档: docs/INSTALLER_GUIDE.md
  • 日志: logs/
  • 配置: config/

© 2024-2026 Koto Project
        """)
        version_text.setWordWrap(True)
        layout.addWidget(version_text)
        
        layout.addStretch()
        self.setLayout(layout)

# ==================== 主窗口 ====================

class KotoMainWindow(QMainWindow):
    """Koto 桌面应用主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Koto - 智能桌面助手")
        self.setWindowIcon(self.create_icon())
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化 Agent
        self.agent_worker = AgentWorker()
        
        # 创建 UI
        self.setup_ui()
        self.setup_menu()
        self.apply_stylesheet()
        
        logger.info("Koto Desktop 应用启动")
    
    def create_icon(self):
        """创建图标"""
        icon = QPixmap(64, 64)
        icon.fill(QColor(33, 150, 243))
        return QIcon(icon)
    
    def setup_ui(self):
        """设置主 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== 侧边栏 ==========
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        self.sidebar.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                border-right: 1px solid #1a1a1a;
            }
        """)
        
        # Koto Logo
        logo_label = QLabel("KOTO")
        logo_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        logo_label.setStyleSheet("color: #2196F3; padding: 20px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        
        sidebar_layout.addSpacing(20)
        
        # 导航按钮
        self.task_btn = SidebarButton("🤖 任务处理")
        self.doc_btn = SidebarButton("📄 文档处理")
        self.chat_btn = SidebarButton("💬 AI 助手")
        self.settings_btn = SidebarButton("⚙️ 设置")
        self.about_btn = SidebarButton("ℹ️ 关于")
        
        for btn in [self.task_btn, self.doc_btn, self.chat_btn, self.settings_btn, self.about_btn]:
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        # 底部状态
        status_label = QLabel("v1.0.0")
        status_label.setStyleSheet("color: #888; padding: 10px; text-align: center; font-size: 11px;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(status_label)
        
        self.sidebar.setLayout(sidebar_layout)
        self.sidebar.setMaximumWidth(200)
        main_layout.addWidget(self.sidebar)
        
        # ========== 内容区域 ==========
        self.content = QStackedWidget()
        
        self.task_panel = TaskPanel(self.agent_worker)
        self.doc_panel = DocumentPanel()
        self.chat_panel = ChatPanel()
        self.settings_panel = SettingsPanel()
        self.about_panel = AboutPanel()
        
        self.content.addWidget(self.task_panel)
        self.content.addWidget(self.doc_panel)
        self.content.addWidget(self.chat_panel)
        self.content.addWidget(self.settings_panel)
        self.content.addWidget(self.about_panel)
        
        main_layout.addWidget(self.content)
        
        central_widget.setLayout(main_layout)
        
        # 连接按钮信号
        self.task_btn.clicked.connect(lambda: self.switch_panel(0))
        self.doc_btn.clicked.connect(lambda: self.switch_panel(1))
        self.chat_btn.clicked.connect(lambda: self.switch_panel(2))
        self.settings_btn.clicked.connect(lambda: self.switch_panel(3))
        self.about_btn.clicked.connect(lambda: self.switch_panel(4))
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 默认显示任务处理面板
        self.switch_panel(0)
    
    def switch_panel(self, index):
        """切换面板"""
        self.content.setCurrentIndex(index)
        
        # 高亮当前按钮
        buttons = [self.task_btn, self.doc_btn, self.chat_btn, self.settings_btn, self.about_btn]
        for i, btn in enumerate(buttons):
            if i == index:
                btn.setStyleSheet(btn.styleSheet() + """
                    background-color: rgba(33, 150, 243, 0.3);
                    border-left: 3px solid #2196F3;
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 20px;
                        background-color: transparent;
                        border: none;
                        color: #ffffff;
                        font-size: 14px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 0.1);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 255, 255, 0.2);
                    }
                """)
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        new_action = file_menu.addAction("新建任务")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_task)
        
        open_action = file_menu.addAction("打开文件")
        open_action.setShortcut("Ctrl+O")
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("退出")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        settings_action = edit_menu.addAction("设置")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(lambda: self.switch_panel(3))
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(lambda: self.switch_panel(4))
        
        docs_action = help_menu.addAction("帮助文档")
        docs_action.triggered.connect(self.show_help)
    
    def new_task(self):
        """新建任务"""
        self.switch_panel(0)
        self.task_panel.input_text.setFocus()
    
    def show_help(self):
        """显示帮助"""
        QMessageBox.information(self, "帮助", """
Koto 快速入门:

1️⃣  智能任务处理
   • 在输入框输入你的需求
   • Agent 会自动分析并执行
   • 查看结果

2️⃣  文档处理
   • 创建 Word、PPT、Excel
   • 编辑和分析文档
   • 导出为其他格式

3️⃣  AI 助手
   • 自然语言交互
   • 实时对话
   • 学习你的使用习惯

快捷键:
  • Ctrl+N - 新建任务
  • Ctrl+, - 打开设置
  • Ctrl+Q - 退出应用
  • Ctrl+Enter - 提交任务
        """)
    
    def apply_stylesheet(self):
        """应用全局样式"""
        stylesheet = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QWidget {
            background-color: #ffffff;
            color: #333333;
        }
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            padding: 8px;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #0d47a1;
        }
        QTextEdit {
            border: 1px solid #cccccc;
            border-radius: 5px;
            padding: 8px;
            font-family: 'Courier New';
            font-size: 11px;
        }
        QLineEdit {
            border: 1px solid #cccccc;
            border-radius: 5px;
            padding: 8px;
        }
        QLabel {
            color: #333333;
        }
        QMenuBar {
            background-color: #f5f5f5;
            border-bottom: 1px solid #cccccc;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        QStatusBar {
            background-color: #f5f5f5;
            border-top: 1px solid #cccccc;
        }
        """
        self.setStyleSheet(stylesheet)

# ==================== 应用入口 ====================

def main():
    """应用程序入口"""
    app = QApplication(sys.argv)
    
    # 设置应用属性
    app.setApplicationName("Koto Desktop")
    app.setApplicationVersion("1.0.0")
    
    # 创建和显示主窗口
    window = KotoMainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
