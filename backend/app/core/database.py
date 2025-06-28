"""
数据库模块（兼容性模块）

此模块保持向后兼容性，实际功能已迁移到 app.db.connections
建议使用新的连接管理器：from app.db.connections.mongodb import mongodb_manager
"""

import logging
from typing import Optional
from pymongo.database import Database
from pymongo.collection import Collection
from ..db.connections.mongodb import mongodb_manager
from .config import settings

logger = logging.getLogger(__name__)

# MongoDB配置 - 从主配置模块获取
def get_mongodb_config():
    """获取MongoDB配置"""
    return {
        "url": settings.MONGODB_URL,
        "db_name": settings.MONGODB_DB
    }

def get_mongodb_client() -> Database:
    """
    获取MongoDB客户端（兼容性函数）

    建议使用新的连接管理器：mongodb_manager.get_sync_database()
    """
    return mongodb_manager.get_sync_database()

def get_collection(collection_name: str) -> Collection:
    """
    获取指定的集合（兼容性函数）

    建议使用新的连接管理器：mongodb_manager.get_sync_collection(collection_name)
    """
    return mongodb_manager.get_sync_collection(collection_name)