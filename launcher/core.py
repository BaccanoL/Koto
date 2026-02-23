"""
Koto 启动协调器 - 统一启动入口
"""
import sys
import os
import logging
from pathlib import Path
from enum import Enum
from datetime import datetime


class LaunchMode(Enum):
    """启动模式枚举"""
    DESKTOP = "desktop"    # 桌面窗口模式（默认）
    SERVER = "server"      # 纯后端服务模式
    REPAIR = "repair"      # 修复诊断模式


class LaunchContext:
    """启动上下文 - 保存环境信息"""
    
    def __init__(self):
        # 项目根目录
        self.root = self._get_root_path()
        
        # 环境检查
        from .health import HealthChecker
        self.checker = HealthChecker(self.root)
        
        self.python_ok, self.python_version = self.checker.check_python_version()
        self.dependencies = self.checker.check_dependencies()
        self.port_status = self.checker.check_port()
        
        # 确定启动模式
        self.mode = self._determine_mode()
    
    def _get_root_path(self) -> Path:
        """获取项目根目录"""
        # 从 launcher 目录的父目录
        return Path(__file__).parent.parent.absolute()
    
    def _determine_mode(self) -> LaunchMode:
        """根据环境和参数决定启动模式"""
        # CLI 参数优先
        if '--server' in sys.argv:
            return LaunchMode.SERVER
        if '--repair' in sys.argv or '--diagnose' in sys.argv:
            return LaunchMode.REPAIR
        
        # 检查核心依赖
        if not self.dependencies.get('flask'):
            return LaunchMode.REPAIR
        
        if not self.dependencies.get('webview'):
            # 没有 webview，但有 flask，可以用服务模式
            if '--no-gui' in sys.argv:
                return LaunchMode.SERVER
            else:
                return LaunchMode.REPAIR
        
        # 端口检查
        if not self.port_status['available'] and not self.port_status['can_cleanup']:
            # 端口被占用且无法清理
            if '--force' not in sys.argv:
                return LaunchMode.REPAIR
        
        # 默认桌面模式
        return LaunchMode.DESKTOP


class Launcher:
    """启动器主控制器"""
    
    def __init__(self):
        self.ctx = LaunchContext()
        self.logger = self._setup_logger()
    
    def run(self):
        """执行启动流程"""
        self._print_banner()
        
        self.logger.info(f"Koto 启动器 v2.0")
        self.logger.info(f"Python: {self.ctx.python_version}")
        self.logger.info(f"工作目录: {self.ctx.root}")
        self.logger.info(f"启动模式: {self.ctx.mode.value}")
        
        # 确保目录存在
        self.ctx.checker.ensure_directories()
        
        # 端口清理（如需要）
        if self.ctx.port_status['can_cleanup'] and not self.ctx.port_status['available']:
            self.logger.warning("⚠️  检测到占用端口的 Koto 进程，尝试清理...")
            if self.ctx.checker.cleanup_stale_koto():
                self.logger.info("✅ 清理成功")
            else:
                self.logger.warning("⚠️  清理失败，可能需要手动处理")
        
        # 根据模式启动
        if self.ctx.mode == LaunchMode.DESKTOP:
            from .modes import DesktopMode
            mode = DesktopMode(self.ctx, self.logger)
        elif self.ctx.mode == LaunchMode.SERVER:
            from .modes import ServerMode
            mode = ServerMode(self.ctx, self.logger)
        else:
            from .modes import RepairMode
            mode = RepairMode(self.ctx, self.logger)
        
        try:
            mode.start()
        except KeyboardInterrupt:
            self.logger.info("\n⚠️  用户中断")
            sys.exit(0)
        except Exception as e:
            self.logger.error(f"❌ 启动失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            sys.exit(1)
    
    def _setup_logger(self) -> logging.Logger:
        """配置统一日志"""
        log_file = self.ctx.root / 'logs' / 'launcher.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建 logger
        logger = logging.getLogger('koto.launcher')
        logger.setLevel(logging.INFO)
        
        # 避免重复添加 handler
        if logger.handlers:
            return logger
        
        # 文件 handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 写入会话分隔符
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"New Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n")
        
        return logger
    
    def _print_banner(self):
        """打印启动横幅"""
        banner = """
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   ██╗  ██╗ ██████╗ ████████╗ ██████╗                             ║
║   ██║ ██╔╝██╔═══██╗╚══██╔══╝██╔═══██╗                            ║
║   █████╔╝ ██║   ██║   ██║   ██║   ██║                            ║
║   ██╔═██╗ ██║   ██║   ██║   ██║   ██║                            ║
║   ██║  ██╗╚██████╔╝   ██║   ╚██████╔╝                            ║
║   ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝                             ║
║                                                                    ║
║                    AI Personal Assistant                           ║
║                        Version 2.0                                 ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
        """
        print(banner)


def main():
    """主入口函数"""
    launcher = Launcher()
    launcher.run()


if __name__ == '__main__':
    main()
