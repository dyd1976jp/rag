"""
MongoDB连接管理器

统一管理MongoDB连接，提供连接池、重连机制和健康检查。
整合原有的分散在多个文件中的MongoDB连接逻辑。
"""

import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from ...core.config import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    MongoDB连接管理器
    
    提供同步和异步的MongoDB连接管理，支持连接池和自动重连。
    设计为单例模式，确保整个应用共享同一个数据库连接。
    """
    
    def __init__(self):
        self._async_client: Optional[AsyncIOMotorClient] = None
        self._async_db: Optional[AsyncIOMotorDatabase] = None
        self._sync_client: Optional[MongoClient] = None
        self._sync_db: Optional[Database] = None
        self._is_connected = False
        
    async def connect_async(self) -> AsyncIOMotorDatabase:
        """
        建立异步MongoDB连接
        
        Returns:
            AsyncIOMotorDatabase: 异步数据库实例
        """
        if self._async_db is None:
            try:
                self._async_client = AsyncIOMotorClient(settings.MONGODB_URL)
                self._async_db = self._async_client[settings.MONGODB_DB]
                
                # 测试连接
                await self._async_db.command('ping')
                self._is_connected = True
                
                logger.info(f"异步MongoDB连接成功: {settings.MONGODB_URL}, 数据库: {settings.MONGODB_DB}")
                
            except Exception as e:
                logger.error(f"异步MongoDB连接失败: {str(e)}")
                raise
                
        return self._async_db
    
    def connect_sync(self) -> Database:
        """
        建立同步MongoDB连接
        
        Returns:
            Database: 同步数据库实例
        """
        if self._sync_db is None:
            try:
                self._sync_client = MongoClient(settings.MONGODB_URL)
                self._sync_db = self._sync_client[settings.MONGODB_DB]
                
                # 测试连接
                self._sync_db.command('ping')
                self._is_connected = True
                
                logger.info(f"同步MongoDB连接成功: {settings.MONGODB_URL}, 数据库: {settings.MONGODB_DB}")
                
            except Exception as e:
                logger.error(f"同步MongoDB连接失败: {str(e)}")
                raise
                
        return self._sync_db
    
    async def close_async(self):
        """关闭异步连接"""
        if self._async_client:
            self._async_client.close()
            self._async_client = None
            self._async_db = None
            logger.info("异步MongoDB连接已关闭")
    
    def close_sync(self):
        """关闭同步连接"""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
            self._sync_db = None
            logger.info("同步MongoDB连接已关闭")
    
    async def get_async_database(self) -> AsyncIOMotorDatabase:
        """获取异步数据库实例"""
        if self._async_db is None:
            await self.connect_async()
        return self._async_db
    
    def get_sync_database(self) -> Database:
        """获取同步数据库实例"""
        if self._sync_db is None:
            self.connect_sync()
        return self._sync_db
    
    async def get_async_collection(self, collection_name: str):
        """获取异步集合"""
        db = await self.get_async_database()
        return db[collection_name]
    
    def get_sync_collection(self, collection_name: str) -> Collection:
        """获取同步集合"""
        db = self.get_sync_database()
        return db[collection_name]
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if self._async_db:
                await self._async_db.command('ping')
                return {"status": "healthy", "type": "async"}
            elif self._sync_db:
                self._sync_db.command('ping')
                return {"status": "healthy", "type": "sync"}
            else:
                return {"status": "disconnected", "type": "none"}
        except Exception as e:
            logger.error(f"MongoDB健康检查失败: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def create_indexes(self):
        """创建必要的索引"""
        try:
            db = await self.get_async_database()
            
            # 文档集合索引
            documents_collection = db.documents
            await documents_collection.create_index("title")
            await documents_collection.create_index("file_path", unique=True)
            await documents_collection.create_index("created_at")
            await documents_collection.create_index("user_id")
            
            # 段落集合索引
            segments_collection = db.document_segments
            await segments_collection.create_index("document_id")
            await segments_collection.create_index("segment_index")
            await segments_collection.create_index([("document_id", 1), ("segment_index", 1)], unique=True)
            
            # 块集合索引
            chunks_collection = db.child_chunks
            await chunks_collection.create_index("parent_segment_id")
            await chunks_collection.create_index("chunk_index")
            await chunks_collection.create_index([("parent_segment_id", 1), ("chunk_index", 1)], unique=True)
            
            logger.info("MongoDB索引创建完成")
            
        except Exception as e:
            logger.error(f"创建MongoDB索引失败: {str(e)}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected


# 创建全局MongoDB管理器实例
mongodb_manager = MongoDBManager()


# 兼容性函数，保持向后兼容
async def get_mongodb_database() -> AsyncIOMotorDatabase:
    """获取MongoDB数据库实例（兼容性函数）"""
    return await mongodb_manager.get_async_database()


def get_mongodb_collection(collection_name: str) -> Collection:
    """获取MongoDB集合（兼容性函数）"""
    return mongodb_manager.get_sync_collection(collection_name)
