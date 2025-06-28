"""
Milvus连接管理器

统一管理Milvus向量数据库连接，提供集合管理和向量操作接口。
整合原有的分散在多个文件中的Milvus连接逻辑。
"""

import logging
from typing import Optional, Dict, Any, List
from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from ...core.config import settings

logger = logging.getLogger(__name__)


class MilvusManager:
    """
    Milvus连接管理器
    
    提供Milvus向量数据库的连接管理、集合操作和向量检索功能。
    设计为单例模式，确保整个应用共享同一个数据库连接。
    """
    
    def __init__(self):
        self._connection_alias = "default"
        self._is_connected = False
        self._collections: Dict[str, Collection] = {}
        
    def connect(self) -> bool:
        """
        连接到Milvus服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 检查是否已连接
            if self._is_connected:
                return True
                
            # 建立连接
            connections.connect(
                alias=self._connection_alias,
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                user=settings.MILVUS_USER,
                password=settings.MILVUS_PASSWORD
            )
            
            self._is_connected = True
            logger.info(f"Milvus连接成功: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"Milvus连接失败: {str(e)}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """断开Milvus连接"""
        try:
            if self._is_connected:
                connections.disconnect(self._connection_alias)
                self._is_connected = False
                self._collections.clear()
                logger.info("Milvus连接已断开")
        except Exception as e:
            logger.error(f"断开Milvus连接失败: {str(e)}")
    
    def create_collection_schema(self, dimension: int = None) -> CollectionSchema:
        """
        创建标准的集合Schema
        
        Args:
            dimension: 向量维度，默认使用配置中的值
            
        Returns:
            CollectionSchema: 集合Schema
        """
        if dimension is None:
            dimension = settings.MILVUS_DIM
            
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="segment_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="RAG文档向量集合",
            enable_dynamic_field=True
        )
        
        return schema
    
    def create_collection(self, collection_name: str = None, dimension: int = None, drop_existing: bool = False) -> Optional[Collection]:
        """
        创建或获取集合
        
        Args:
            collection_name: 集合名称，默认使用配置中的值
            dimension: 向量维度
            drop_existing: 是否删除已存在的集合
            
        Returns:
            Collection: 集合实例
        """
        if not self.connect():
            return None
            
        if collection_name is None:
            collection_name = settings.MILVUS_COLLECTION
            
        try:
            # 检查集合是否存在
            if utility.has_collection(collection_name):
                if drop_existing:
                    utility.drop_collection(collection_name)
                    logger.info(f"已删除现有集合: {collection_name}")
                else:
                    collection = Collection(collection_name)
                    self._collections[collection_name] = collection
                    logger.info(f"使用现有集合: {collection_name}")
                    return collection
            
            # 创建新集合
            schema = self.create_collection_schema(dimension)
            collection = Collection(
                name=collection_name,
                schema=schema,
                using=self._connection_alias
            )
            
            # 创建索引
            self.create_index(collection)
            
            self._collections[collection_name] = collection
            logger.info(f"创建新集合成功: {collection_name}")
            return collection
            
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            return None
    
    def create_index(self, collection: Collection):
        """
        为集合创建索引
        
        Args:
            collection: 集合实例
        """
        try:
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            
            collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            
            logger.info(f"为集合 {collection.name} 创建索引成功")
            
        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
            raise
    
    def get_collection(self, collection_name: str = None) -> Optional[Collection]:
        """
        获取集合实例
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Collection: 集合实例
        """
        if collection_name is None:
            collection_name = settings.MILVUS_COLLECTION
            
        # 从缓存中获取
        if collection_name in self._collections:
            return self._collections[collection_name]
            
        # 尝试连接并获取集合
        if not self.connect():
            return None
            
        try:
            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                self._collections[collection_name] = collection
                return collection
            else:
                logger.warning(f"集合不存在: {collection_name}")
                return None
                
        except Exception as e:
            logger.error(f"获取集合失败: {str(e)}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self._is_connected:
                if not self.connect():
                    return {"status": "disconnected", "error": "无法连接到Milvus"}
            
            # 检查默认集合
            collection = self.get_collection()
            if collection:
                collection.load()
                return {
                    "status": "healthy",
                    "collection": collection.name,
                    "num_entities": collection.num_entities
                }
            else:
                return {"status": "no_collection", "error": "默认集合不存在"}
                
        except Exception as e:
            logger.error(f"Milvus健康检查失败: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            if not self.connect():
                return []
            return utility.list_collections()
        except Exception as e:
            logger.error(f"列出集合失败: {str(e)}")
            return []
    
    def get_collection_stats(self, collection_name: str = None) -> Dict[str, Any]:
        """获取集合统计信息"""
        collection = self.get_collection(collection_name)
        if not collection:
            return {}
            
        try:
            collection.load()
            return {
                "name": collection.name,
                "num_entities": collection.num_entities,
                "schema": {
                    "fields": [field.name for field in collection.schema.fields],
                    "description": collection.schema.description
                }
            }
        except Exception as e:
            logger.error(f"获取集合统计失败: {str(e)}")
            return {}
    
    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected


# 创建全局Milvus管理器实例
milvus_manager = MilvusManager()


# 兼容性函数，保持向后兼容
def get_milvus_collection(collection_name: str = None) -> Optional[Collection]:
    """获取Milvus集合（兼容性函数）"""
    return milvus_manager.get_collection(collection_name)
