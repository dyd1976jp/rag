import logging
import sys
from pathlib import Path
from loguru import logger

def setup_logging():
    # 创建日志目录
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    # 配置日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 移除默认的处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level="INFO",
        colorize=True
    )
    
    # 添加文件输出
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        format=log_format,
        level="DEBUG",
        encoding="utf-8"
    )
    
    # 配置 uvicorn 的日志
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        ) 