"""
Milvus连接管理模块（兼容性模块）

此模块保持向后兼容性，实际功能已迁移到 connections/milvus.py
建议使用新的连接管理器：from app.db.connections.milvus import milvus_manager
"""

import logging
from pymilvus import Collection
from .connections.milvus import milvus_manager
from ..core.config import settings

logger = logging.getLogger(__name__)

# 向后兼容性类
class MilvusDB:
    """
    Milvus连接管理类（兼容性包装）

    为了保持向后兼容性而保留的类，实际功能委托给新的连接管理器。
    """
    def __init__(self):
        self._manager = milvus_manager
        self._collection: Collection = None

    def connect(self):
        """连接到Milvus"""
        if self._manager.connect():
            # 获取或创建默认集合
            self._collection = self._manager.get_collection(settings.MILVUS_COLLECTION)
            if self._collection is None:
                # 如果集合不存在，创建集合
                self._collection = self._manager.create_collection(
                    collection_name=settings.MILVUS_COLLECTION,
                    dimension=settings.MILVUS_DIM,
                    drop_existing=False
                )
                if self._collection:
                    logger.info(f"集合 {settings.MILVUS_COLLECTION} 创建成功")
                else:
                    logger.error(f"集合 {settings.MILVUS_COLLECTION} 创建失败")
                    raise Exception("集合创建失败")
            else:
                logger.info(f"使用现有集合: {settings.MILVUS_COLLECTION}")

    def disconnect(self):
        """断开连接"""
        self._manager.disconnect()

    @property
    def collection(self) -> Collection:
        """获取集合（兼容性属性）"""
        if self._collection is None:
            self.connect()
        return self._collection

# 创建全局 Milvus 实例（兼容性）
milvus_db = MilvusDB()

# 推荐使用的新接口
__all__ = ["milvus_db", "milvus_manager"]