"""
基础仓储类

定义仓储模式的基础接口和通用功能。
所有具体的仓储类都应该继承自这个基础类。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.database import Database
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    基础仓储抽象类
    
    定义了仓储模式的基本接口，包括CRUD操作和查询方法。
    支持同步和异步操作。
    """
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._async_collection: Optional[AsyncIOMotorCollection] = None
        self._sync_collection: Optional[Collection] = None
    
    def set_async_database(self, db: AsyncIOMotorDatabase):
        """设置异步数据库连接"""
        self._async_collection = db[self.collection_name]
    
    def set_sync_database(self, db: Database):
        """设置同步数据库连接"""
        self._sync_collection = db[self.collection_name]
    
    @property
    def async_collection(self) -> AsyncIOMotorCollection:
        """获取异步集合"""
        if self._async_collection is None:
            raise RuntimeError("异步数据库连接未设置")
        return self._async_collection
    
    @property
    def sync_collection(self) -> Collection:
        """获取同步集合"""
        if self._sync_collection is None:
            raise RuntimeError("同步数据库连接未设置")
        return self._sync_collection
    
    # 抽象方法，子类必须实现
    @abstractmethod
    def to_dict(self, entity: T) -> Dict[str, Any]:
        """将实体对象转换为字典"""
        pass
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> T:
        """从字典创建实体对象"""
        pass
    
    # 异步CRUD操作
    async def create_async(self, entity: T) -> str:
        """
        异步创建实体
        
        Args:
            entity: 要创建的实体对象
            
        Returns:
            str: 创建的实体ID
        """
        try:
            data = self.to_dict(entity)
            result = await self.async_collection.insert_one(data)
            logger.info(f"创建实体成功: {self.collection_name}, ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"创建实体失败: {self.collection_name}, 错误: {str(e)}")
            raise
    
    async def get_by_id_async(self, entity_id: str) -> Optional[T]:
        """
        异步根据ID获取实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            Optional[T]: 实体对象或None
        """
        try:
            from bson import ObjectId
            data = await self.async_collection.find_one({"_id": ObjectId(entity_id)})
            if data:
                return self.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"根据ID获取实体失败: {self.collection_name}, ID: {entity_id}, 错误: {str(e)}")
            return None
    
    async def update_async(self, entity_id: str, update_data: Dict[str, Any]) -> bool:
        """
        异步更新实体
        
        Args:
            entity_id: 实体ID
            update_data: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            from bson import ObjectId
            result = await self.async_collection.update_one(
                {"_id": ObjectId(entity_id)},
                {"$set": update_data}
            )
            success = result.modified_count > 0
            if success:
                logger.info(f"更新实体成功: {self.collection_name}, ID: {entity_id}")
            return success
        except Exception as e:
            logger.error(f"更新实体失败: {self.collection_name}, ID: {entity_id}, 错误: {str(e)}")
            return False
    
    async def delete_async(self, entity_id: str) -> bool:
        """
        异步删除实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            from bson import ObjectId
            result = await self.async_collection.delete_one({"_id": ObjectId(entity_id)})
            success = result.deleted_count > 0
            if success:
                logger.info(f"删除实体成功: {self.collection_name}, ID: {entity_id}")
            return success
        except Exception as e:
            logger.error(f"删除实体失败: {self.collection_name}, ID: {entity_id}, 错误: {str(e)}")
            return False
    
    async def find_async(self, filter_dict: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[T]:
        """
        异步查询实体列表
        
        Args:
            filter_dict: 查询条件
            limit: 限制数量
            skip: 跳过数量
            
        Returns:
            List[T]: 实体列表
        """
        try:
            cursor = self.async_collection.find(filter_dict).skip(skip).limit(limit)
            entities = []
            async for data in cursor:
                entities.append(self.from_dict(data))
            return entities
        except Exception as e:
            logger.error(f"查询实体列表失败: {self.collection_name}, 错误: {str(e)}")
            return []
    
    async def count_async(self, filter_dict: Dict[str, Any] = None) -> int:
        """
        异步统计实体数量
        
        Args:
            filter_dict: 查询条件
            
        Returns:
            int: 实体数量
        """
        try:
            if filter_dict is None:
                filter_dict = {}
            return await self.async_collection.count_documents(filter_dict)
        except Exception as e:
            logger.error(f"统计实体数量失败: {self.collection_name}, 错误: {str(e)}")
            return 0
    
    # 同步CRUD操作（简化版本）
    def create_sync(self, entity: T) -> str:
        """同步创建实体"""
        try:
            data = self.to_dict(entity)
            result = self.sync_collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"同步创建实体失败: {self.collection_name}, 错误: {str(e)}")
            raise
    
    def get_by_id_sync(self, entity_id: str) -> Optional[T]:
        """同步根据ID获取实体"""
        try:
            from bson import ObjectId
            data = self.sync_collection.find_one({"_id": ObjectId(entity_id)})
            if data:
                return self.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"同步根据ID获取实体失败: {self.collection_name}, 错误: {str(e)}")
            return None
    
    def find_sync(self, filter_dict: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[T]:
        """同步查询实体列表"""
        try:
            cursor = self.sync_collection.find(filter_dict).skip(skip).limit(limit)
            return [self.from_dict(data) for data in cursor]
        except Exception as e:
            logger.error(f"同步查询实体列表失败: {self.collection_name}, 错误: {str(e)}")
            return []
