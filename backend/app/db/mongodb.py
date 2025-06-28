"""
MongoDB连接管理模块（兼容性模块）

此模块保持向后兼容性，实际功能已迁移到 connections/mongodb.py
建议使用新的连接管理器：from app.db.connections.mongodb import mongodb_manager
"""

import logging
from .connections.mongodb import mongodb_manager

logger = logging.getLogger(__name__)

# 向后兼容性类
class MongoDB:
    """
    MongoDB连接管理类（兼容性包装）

    为了保持向后兼容性而保留的类，实际功能委托给新的连接管理器。
    """
    def __init__(self):
        self._manager = mongodb_manager

    async def connect(self):
        """异步连接到 MongoDB"""
        await self._manager.connect_async()

    async def close(self):
        """异步关闭连接"""
        await self._manager.close_async()

    @property
    def client(self):
        """获取客户端（兼容性属性）"""
        return self._manager._async_client

    @property
    def db(self):
        """获取数据库（兼容性属性）"""
        return self._manager._async_db

# 创建全局 MongoDB 实例（兼容性）
mongodb = MongoDB()

# 推荐使用的新接口
__all__ = ["mongodb", "mongodb_manager"]