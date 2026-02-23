"""
Koto 应用日志系统
支持控制台和文件输出、日志级别控制、结构化日志
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[92m',     # 绿色
        'WARNING': '\033[93m',  # 黄色
        'ERROR': '\033[91m',    # 红色
        'CRITICAL': '\033[41m', # 红色背景
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        max_bytes: 日志文件最大大小
        backup_count: 备份文件数量
        format_string: 日志格式字符串
    
    Returns:
        配置好的日志记录器
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    if logger.handlers:
        return logger  # 避免重复配置
    
    # 默认格式
    if not format_string:
        format_string = "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    console_formatter = ColoredFormatter(format_string)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # 文件保存所有级别
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)

# 创建应用主日志记录器
app_logger = setup_logger(
    'koto',
    level='INFO',
    log_file='logs/koto.log',
    format_string='[%(asctime)s] [%(levelname)s] %(name)s - %(message)s'
)

# 为各模块创建特定的日志记录器
stream_logger = get_logger('koto.stream')
interrupt_logger = get_logger('koto.interrupt')
session_logger = get_logger('koto.session')
error_logger = get_logger('koto.error')

if __name__ == "__main__":
    # 测试日志
    logger = app_logger
    
    logger.debug("这是一条调试信息")
    logger.info("应用启动成功")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    print("\n✅ 日志系统测试完成")
