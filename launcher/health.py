"""
启动器健康检查模块
检测系统环境、端口、依赖等
"""
import sys
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self, root_path: Path):
        self.root = root_path
    
    def check_python_version(self) -> Tuple[bool, str]:
        """检查 Python 版本"""
        version = sys.version_info
        if version >= (3, 9):
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        return False, f"Python 版本过低 ({version.major}.{version.minor}), 需要 >= 3.9"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """检查关键依赖包"""
        deps = {
            'flask': False,
            'webview': False,
            'psutil': False,
        }
        
        for pkg in deps:
            try:
                __import__(pkg)
                deps[pkg] = True
            except ImportError:
                pass
        
        return deps
    
    def check_port(self, port: int = 5000) -> Dict[str, any]:
        """
        检查端口状态
        返回: {
            'available': bool,
            'occupied_by': Optional[int],  # PID
            'can_cleanup': bool
        }
        """
        result = {
            'available': False,
            'occupied_by': None,
            'can_cleanup': False
        }
        
        # 先检查端口是否可以绑定
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                result['available'] = True
                return result
        except OSError:
            pass  # 端口被占用，继续检查
        
        # 使用 psutil 查找占用进程
        if not PSUTIL_AVAILABLE:
            return result
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                if (conn.laddr.port == port and 
                    conn.status == psutil.CONN_LISTEN):
                    result['occupied_by'] = conn.pid
                    
                    # 检查是否是 Koto 进程
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            name = proc.name().lower()
                            cmdline = ' '.join(proc.cmdline()).lower()
                            
                            if 'koto' in name or 'koto_app' in cmdline or 'pythonw' in name:
                                result['can_cleanup'] = True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    break
        except Exception:
            pass
        
        return result
    
    def cleanup_stale_koto(self, port: int = 5000) -> bool:
        """
        清理占用端口的过期 Koto 进程
        返回: True 表示成功清理
        """
        if not PSUTIL_AVAILABLE:
            return False
        
        info = self.check_port(port)
        if not info['can_cleanup'] or not info['occupied_by']:
            return False
        
        try:
            proc = psutil.Process(info['occupied_by'])
            proc.terminate()
            proc.wait(timeout=3)
            return True
        except Exception:
            # 如果 terminate 失败，尝试 kill
            try:
                proc.kill()
                return True
            except Exception:
                return False
    
    def check_config_files(self) -> Dict[str, bool]:
        """检查必要的配置文件"""
        checks = {
            'gemini_config': (self.root / 'config' / 'gemini_config.env').exists(),
            'user_settings': (self.root / 'config' / 'user_settings.json').exists(),
        }
        return checks
    
    def ensure_directories(self) -> None:
        """确保必要的目录存在"""
        dirs = [
            'workspace',
            'workspace/images',
            'workspace/documents',
            'workspace/code',
            'chats',
            'logs',
            'config'
        ]
        
        for d in dirs:
            (self.root / d).mkdir(parents=True, exist_ok=True)
    
    def get_health_report(self) -> Dict:
        """
        获取完整健康报告
        返回格式:
        {
            'python_ok': bool,
            'python_version': str,
            'dependencies': {...},
            'port_status': {...},
            'config_files': {...},
            'overall_ok': bool
        }
        """
        python_ok, python_ver = self.check_python_version()
        deps = self.check_dependencies()
        port_status = self.check_port()
        config_files = self.check_config_files()
        
        # 核心依赖检查
        core_deps_ok = deps.get('flask', False) and deps.get('webview', False)
        
        report = {
            'python_ok': python_ok,
            'python_version': python_ver,
            'dependencies': deps,
            'port_status': port_status,
            'config_files': config_files,
            'overall_ok': python_ok and core_deps_ok and (port_status['available'] or port_status['can_cleanup'])
        }
        
        return report


def wait_for_port(host: str = '127.0.0.1', port: int = 5000, timeout: int = 3) -> bool:
    """
    等待端口就绪
    返回: True 表示端口可连接
    """
    import time
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex((host, port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    
    return False


def check_http_health(url: str = 'http://127.0.0.1:5000/api/health', timeout: int = 2) -> bool:
    """
    检查 HTTP 服务健康状态
    返回: True 表示服务正常响应
    """
    try:
        from urllib.request import urlopen, build_opener, ProxyHandler
        opener = build_opener(ProxyHandler({}))  # 禁用代理
        
        with opener.open(url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False
