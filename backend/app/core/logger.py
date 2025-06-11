import logging
from logging.handlers import RotatingFileHandler
import sys
from .paths import (
    API_LOGS_DIR,
    WORKER_LOGS_DIR,
    DEBUG_LOGS_DIR,
    TEST_LOGS_DIR
)

def setup_logger(name: str, log_dir, level=logging.INFO):
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    file_handler = RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# API日志
api_logger = setup_logger('api', API_LOGS_DIR)

# 后台任务日志
worker_logger = setup_logger('worker', WORKER_LOGS_DIR)

# 调试日志
debug_logger = setup_logger('debug', DEBUG_LOGS_DIR, level=logging.DEBUG)

# 测试日志
test_logger = setup_logger('test', TEST_LOGS_DIR) 