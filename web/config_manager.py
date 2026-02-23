"""
Koto 应用配置管理模块
支持多环境配置、环境变量覆盖、配置验证
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class APIConfig:
    """API 配置"""
    gemini_api_key: str
    gemini_timeout: int = 120  # 秒
    gemini_connect_timeout: int = 20
    
    def validate(self):
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 未配置")
        if self.gemini_timeout <= 0:
            raise ValueError("超时时间必须大于 0")

@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    workers: int = 1
    
    def validate(self):
        if self.port < 1 or self.port > 65535:
            raise ValueError("端口号必须在 1-65535 之间")

@dataclass
class StorageConfig:
    """存储配置"""
    chat_dir: str = "chats"
    workspace_dir: str = "workspace"
    upload_dir: str = "web/uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    def validate(self):
        if self.max_file_size <= 0:
            raise ValueError("最大文件大小必须大于 0")

@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    file: Optional[str] = "logs/koto.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format: str = "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    
    def validate(self):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level not in valid_levels:
            raise ValueError(f"日志级别必须是: {valid_levels}")

@dataclass
class FeatureConfig:
    """功能配置"""
    enable_interrupt: bool = True
    enable_session_isolation: bool = True
    enable_auto_save: bool = True
    session_timeout: int = 3600  # 秒
    max_concurrent_sessions: int = 10

class Config:
    """主配置类"""
    
    def __init__(self, env_file: Optional[str] = None, env: str = "production"):
        self.env = env
        self.env_file = env_file or f"config/{env}.env"
        
        # 加载基础配置
        self.api = APIConfig(
            gemini_api_key=self._get_env("GEMINI_API_KEY", "")
        )
        self.server = ServerConfig(
            host=self._get_env("SERVER_HOST", "127.0.0.1"),
            port=int(self._get_env("SERVER_PORT", "5000")),
            debug=self._get_env("DEBUG", "false").lower() == "true",
            workers=int(self._get_env("WORKERS", "1"))
        )
        self.storage = StorageConfig(
            chat_dir=self._get_env("CHAT_DIR", "chats"),
            workspace_dir=self._get_env("WORKSPACE_DIR", "workspace"),
            upload_dir=self._get_env("UPLOAD_DIR", "web/uploads")
        )
        self.log = LogConfig(
            level=self._get_env("LOG_LEVEL", "INFO"),
            file=self._get_env("LOG_FILE", "logs/koto.log")
        )
        self.feature = FeatureConfig()
        
        # 验证配置
        self.validate()
        
        # 创建必要的目录
        self._create_directories()
    
    def _get_env(self, key: str, default: str = "") -> str:
        """从环境变量或配置文件获取值"""
        # 优先级：环境变量 > .env 文件 > 默认值
        if key in os.environ:
            return os.environ[key]
        
        value = self._read_env_file(key)
        return value if value is not None else default
    
    def _read_env_file(self, key: str) -> Optional[str]:
        """从 .env 文件读取"""
        if not os.path.exists(self.env_file):
            return None
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        if k.strip() == key:
                            return v.strip().strip('"\'')
        except Exception:
            pass
        
        return None
    
    def _create_directories(self):
        """创建必要的目录"""
        dirs = [
            self.storage.chat_dir,
            self.storage.workspace_dir,
            self.storage.upload_dir,
            os.path.dirname(self.log.file) if self.log.file else None
        ]
        
        for d in dirs:
            if d:
                Path(d).mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """验证所有配置"""
        self.api.validate()
        self.server.validate()
        self.storage.validate()
        self.log.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'env': self.env,
            'api': asdict(self.api),
            'server': asdict(self.server),
            'storage': asdict(self.storage),
            'log': asdict(self.log),
            'feature': asdict(self.feature)
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        config_dict = self.to_dict()
        # 移除敏感信息
        config_dict['api']['gemini_api_key'] = '***'
        return json.dumps(config_dict, indent=2, ensure_ascii=False)


# 全局配置实例
def get_config(env: str = "production") -> Config:
    """获取配置实例"""
    return Config(env=env)


if __name__ == "__main__":
    # 测试配置
    try:
        cfg = get_config()
        print("✅ 配置加载成功")
        print(cfg.to_json())
    except Exception as e:
        print(f"❌ 配置错误: {e}")
