"""
MongoDB数据库连接管理模块

本模块负责管理应用程序与MongoDB数据库的连接，提供：
1. 数据库连接的初始化和关闭
2. 统一的数据库实例访问点
3. 异步连接支持

使用motor作为MongoDB的异步驱动，支持FastAPI的异步操作模式。
"""

import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class MongoDB:
    """
    MongoDB连接管理类
    
    管理与MongoDB数据库的异步连接生命周期，提供数据库客户端和数据库实例。
    设计为单例模式，确保整个应用共享同一个数据库连接。
    """
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        """异步连接到 MongoDB"""
        try:
            # 从环境变量获取连接信息
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
            db_name = os.environ.get("MONGODB_DB", "rag_chat")
            
            # 创建异步客户端
            self.client = AsyncIOMotorClient(mongo_uri)
            self.db = self.client[db_name]
            
            # 测试连接
            await self.db.command('ping')
            
            logger.info(f"成功连接到 MongoDB: {mongo_uri}, 数据库: {db_name}")
            
        except Exception as e:
            logger.error(f"连接 MongoDB 失败: {str(e)}")
            raise
            
    async def close(self):
        """异步关闭连接"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB 连接已关闭")

# 创建全局 MongoDB 实例
mongodb = MongoDB() 