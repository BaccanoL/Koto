"""
启动模式实现
Desktop: 桌面窗口模式
Server: 纯后端服务模式
Repair: 修复诊断模式
"""
import sys
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import LaunchContext
    import logging

from .health import wait_for_port, check_http_health


class BaseMode:
    """启动模式基类"""
    
    def __init__(self, ctx: 'LaunchContext', logger: 'logging.Logger'):
        self.ctx = ctx
        self.logger = logger
        self.root = ctx.root
    
    def start(self):
        """启动模式（子类实现）"""
        raise NotImplementedError


class DesktopMode(BaseMode):
    """桌面窗口模式 - 默认启动模式"""
    
    def start(self):
        self.logger.info("🖥️  启动桌面模式...")
        
        # 1. 启动 Flask 后台线程
        self.logger.info("⚙️  启动 Flask 后端...")
        flask_thread = threading.Thread(
            target=self._start_flask,
            daemon=True,
            name="FlaskServerThread"
        )
        flask_thread.start()
        
        # 2. 等待 Flask 就绪（最多 5 秒）
        self.logger.info("⏳ 等待后端就绪...")
        if not wait_for_port('127.0.0.1', 5000, timeout=5):
            self.logger.error("❌ Flask 启动超时")
            self._fallback_to_repair("Flask 后端启动超时，可能端口被占用或依赖缺失")
            return
        
        self.logger.info("✅ 后端就绪")
        
        # 3. 健康检查
        if not check_http_health():
            self.logger.warning("⚠️  健康检查失败，但继续启动")
        
        # 4. 启动 pywebview 窗口（同步阻塞）
        self._start_window()
    
    def _start_flask(self):
        """后台启动 Flask（在独立线程中）"""
        try:
            # 设置工作目录
            os.chdir(str(self.root))
            
            # 添加路径
            if str(self.root) not in sys.path:
                sys.path.insert(0, str(self.root))
            
            # 导入并运行 Flask app
            from web.app import app
            
            # 禁用 Flask 日志输出（减少噪音）
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.WARNING)
            
            self.logger.info("🚀 Flask 服务启动中...")
            app.run(
                host='127.0.0.1',
                port=5000,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"❌ Flask 启动失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _start_window(self):
        """启动 pywebview 窗口"""
        try:
            import webview
            
            self.logger.info("🪟 创建窗口...")
            
            # 窗口图标
            icon_path = self.root / 'assets' / 'koto_icon.ico'
            icon = str(icon_path) if icon_path.exists() else None
            
            # 创建窗口
            window = webview.create_window(
                title='Koto - AI 个人助手',
                url='http://127.0.0.1:5000',
                width=1200,
                height=800,
                resizable=True,
                fullscreen=False,
                min_size=(800, 600),
                confirm_close=False,
            )
            
            # 启动事件循环
            self.logger.info("✅ 窗口创建成功，启动事件循环...")
            
            start_kwargs = {'debug': False}
            if icon:
                start_kwargs['icon'] = icon
            
            webview.start(**start_kwargs)
            
            self.logger.info("ℹ️  窗口已关闭")
            
        except ImportError as e:
            self.logger.error(f"❌ pywebview 未安装: {e}")
            self._fallback_to_repair("pywebview 未安装，请运行: pip install pywebview")
        except Exception as e:
            self.logger.error(f"❌ 窗口启动失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _fallback_to_repair(self, reason: str):
        """切换到修复模式"""
        self.logger.warning(f"⚠️  切换到修复模式: {reason}")
        repair = RepairMode(self.ctx, self.logger)
        repair.start()


class ServerMode(BaseMode):
    """纯后端服务模式（无 UI）"""
    
    def start(self):
        self.logger.info("🌐 启动服务模式（无 UI）...")
        
        # 设置工作目录
        os.chdir(str(self.root))
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        
        try:
            from web.app import app
            
            self.logger.info("🚀 Flask 服务启动（0.0.0.0:5000）...")
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=False,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"❌ 服务启动失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            sys.exit(1)


class RepairMode(BaseMode):
    """修复诊断模式"""
    
    def start(self):
        self.logger.warning("🔧 进入修复诊断模式...")
        
        from .health import HealthChecker
        checker = HealthChecker(self.root)
        
        report = checker.get_health_report()
        
        self._show_diagnosis(report)
    
    def _show_diagnosis(self, report: dict):
        """显示诊断信息"""
        print("\n" + "="*70)
        print("  🔧 Koto 修复向导")
        print("="*70)
        
        # Python 版本
        if report['python_ok']:
            print(f"✅ Python: {report['python_version']}")
        else:
            print(f"❌ Python: {report['python_version']}")
            print("   需要 Python >= 3.9")
        
        # 依赖检查
        print("\n📦 依赖检查:")
        deps = report['dependencies']
        for pkg, installed in deps.items():
            status = "✅" if installed else "❌"
            print(f"   {status} {pkg}")
        
        if not all(deps.values()):
            print("\n💡 安装缺失依赖:")
            print("   pip install -r requirements.txt")
        
        # 端口检查
        print("\n🔌 端口检查:")
        port_status = report['port_status']
        if port_status['available']:
            print("   ✅ 端口 5000 可用")
        elif port_status['can_cleanup']:
            print(f"   ⚠️  端口 5000 被进程 {port_status['occupied_by']} 占用")
            print("   可以自动清理（进程是 Koto）")
            
            # 询问是否清理
            response = input("\n是否清理占用进程? (y/N): ").strip().lower()
            if response == 'y':
                from .health import HealthChecker
                checker = HealthChecker(self.root)
                if checker.cleanup_stale_koto():
                    print("✅ 清理成功！")
                    print("请重新运行 Koto")
                else:
                    print("❌ 清理失败")
        else:
            print(f"   ❌ 端口 5000 被其他程序占用 (PID: {port_status['occupied_by']})")
            print("   请手动关闭占用进程或使用其他端口")
        
        # 配置文件
        print("\n⚙️  配置文件:")
        configs = report['config_files']
        for name, exists in configs.items():
            status = "✅" if exists else "⚠️ "
            print(f"   {status} {name}")
        
        # 总体状态
        print("\n" + "="*70)
        if report['overall_ok']:
            print("✅ 系统检查通过，可以正常启动")
            print("\n💡 提示: 运行 'python launcher.py' 启动 Koto")
        else:
            print("❌ 系统检查未通过，请解决上述问题")
        print("="*70)
        
        # 详细日志
        print(f"\n📋 详细日志: {self.root / 'logs' / 'launcher.log'}")
        print()
        
        input("按回车键退出...")
