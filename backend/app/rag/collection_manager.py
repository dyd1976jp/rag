"""
Milvus集合管理工具

统一管理Milvus集合的创建、更新和维护，确保schema定义的一致性和动态字段支持。
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema, DataType, 
    utility, Index
)

from .constants import Field, DEFAULT_COLLECTION_NAME, VECTOR_STORE_CONFIG
from ..core.config import settings

logger = logging.getLogger(__name__)


class MilvusCollectionManager:
    """Milvus集合管理器"""
    
    def __init__(self, host: str = None, port: int = None):
        """
        初始化集合管理器
        
        Args:
            host: Milvus服务器主机名
            port: Milvus服务器端口
        """
        self.host = host or settings.MILVUS_HOST
        self.port = port or settings.MILVUS_PORT
        self._connected = False
        
    def connect(self) -> bool:
        """连接到Milvus服务器"""
        try:
            if not self._connected:
                connections.connect(host=self.host, port=self.port)
                self._connected = True
                logger.info(f"成功连接到Milvus服务器: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接Milvus服务器失败: {e}")
            return False
    
    def disconnect(self):
        """断开Milvus连接"""
        try:
            if self._connected:
                # 获取所有连接并断开
                try:
                    connections.disconnect("default")
                except:
                    # 如果没有default连接，尝试断开所有连接
                    pass
                self._connected = False
                logger.info("已断开Milvus连接")
        except Exception as e:
            logger.warning(f"断开连接时出错: {e}")
    
    def create_standard_schema(self, dimension: int = 768) -> CollectionSchema:
        """
        创建标准的集合schema
        
        Args:
            dimension: 向量维度，默认768（适用于nomic-embed-text-v1.5）
            
        Returns:
            CollectionSchema: 集合schema对象
        """
        fields = [
            # 主键字段
            FieldSchema(
                name=Field.PRIMARY_KEY.value,
                dtype=DataType.VARCHAR,
                is_primary=True,
                auto_id=False,
                max_length=100,
                description="文档唯一标识符"
            ),
            # 向量字段
            FieldSchema(
                name=Field.VECTOR.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="文档嵌入向量"
            ),
            # 内容字段
            FieldSchema(
                name=Field.CONTENT_KEY.value,
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="文档文本内容"
            ),
            # 元数据字段（JSON类型支持动态结构）
            FieldSchema(
                name=Field.METADATA_KEY.value,
                dtype=DataType.JSON,
                description="文档元数据（JSON格式）"
            ),
            # 分组字段
            FieldSchema(
                name=Field.GROUP_KEY.value,
                dtype=DataType.VARCHAR,
                max_length=100,
                description="文档分组标识"
            ),
            # 稀疏向量字段（可选）
            FieldSchema(
                name=Field.SPARSE_VECTOR.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="稀疏向量（用于混合检索）"
            )
        ]
        
        # 创建schema，启用动态字段支持
        schema = CollectionSchema(
            fields=fields,
            description="RAG系统文档向量存储集合（支持动态字段）",
            enable_dynamic_field=True  # 启用动态字段支持
        )
        
        return schema
    
    def create_collection(self, 
                         collection_name: str, 
                         dimension: int = 768,
                         drop_existing: bool = False) -> Optional[Collection]:
        """
        创建集合
        
        Args:
            collection_name: 集合名称
            dimension: 向量维度
            drop_existing: 是否删除已存在的集合
            
        Returns:
            Collection: 创建的集合对象，失败时返回None
        """
        if not self.connect():
            return None
            
        try:
            # 检查集合是否存在
            if utility.has_collection(collection_name):
                if drop_existing:
                    logger.info(f"删除已存在的集合: {collection_name}")
                    utility.drop_collection(collection_name)
                else:
                    logger.info(f"集合 {collection_name} 已存在，直接加载")
                    collection = Collection(collection_name)
                    return collection
            
            # 创建新集合
            logger.info(f"创建新集合: {collection_name}")
            schema = self.create_standard_schema(dimension)
            collection = Collection(name=collection_name, schema=schema)

            # 自动创建索引
            logger.info("为新集合创建索引...")
            if self.create_indexes(collection):
                logger.info(f"集合 {collection_name} 创建成功")
                logger.info(f"动态字段支持: {schema.enable_dynamic_field}")
            else:
                logger.warning("索引创建失败，但集合已创建")

            return collection
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return None
    
    def create_indexes(self, collection: Collection, 
                      vector_field: str = None,
                      sparse_vector_field: str = None) -> bool:
        """
        为集合创建索引
        
        Args:
            collection: 集合对象
            vector_field: 向量字段名
            sparse_vector_field: 稀疏向量字段名
            
        Returns:
            bool: 创建成功返回True
        """
        try:
            vector_field = vector_field or Field.VECTOR.value
            sparse_vector_field = sparse_vector_field or Field.SPARSE_VECTOR.value
            
            # 获取集合实体数量以选择合适的索引类型
            num_entities = collection.num_entities
            
            # 根据数据量选择索引配置
            if num_entities < 1000:
                index_config = VECTOR_STORE_CONFIG["index_params"]["small"]
            elif num_entities < 10000:
                index_config = VECTOR_STORE_CONFIG["index_params"]["medium"]
            else:
                index_config = VECTOR_STORE_CONFIG["index_params"]["large"]
            
            # 为主向量字段创建索引
            logger.info(f"为字段 {vector_field} 创建索引: {index_config['index_type']}")
            collection.create_index(
                field_name=vector_field,
                index_params=index_config
            )
            
            # 为稀疏向量字段创建索引（如果存在）
            try:
                collection.create_index(
                    field_name=sparse_vector_field,
                    index_params={
                        "index_type": "IVF_FLAT",
                        "metric_type": "L2",
                        "params": {"nlist": 1024}
                    }
                )
                logger.info(f"为字段 {sparse_vector_field} 创建索引成功")
            except Exception as e:
                logger.warning(f"为稀疏向量字段创建索引失败: {e}")
            
            logger.info("索引创建完成")
            return True
            
        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Dict: 集合信息
        """
        if not self.connect():
            return {}
            
        try:
            if not utility.has_collection(collection_name):
                return {"exists": False}
            
            collection = Collection(collection_name)
            schema = collection.schema
            
            info = {
                "exists": True,
                "name": collection_name,
                "description": schema.description,
                "enable_dynamic_field": schema.enable_dynamic_field,
                "num_entities": collection.num_entities,
                "fields": [],
                "indexes": []
            }
            
            # 字段信息
            for field in schema.fields:
                field_info = {
                    "name": field.name,
                    "type": str(field.dtype),
                    "is_primary": field.is_primary,
                    "auto_id": getattr(field, 'auto_id', False)
                }
                
                if hasattr(field, 'max_length') and field.max_length:
                    field_info["max_length"] = field.max_length
                if hasattr(field, 'dim') and field.dim:
                    field_info["dimension"] = field.dim
                    
                info["fields"].append(field_info)
            
            # 索引信息
            for index in collection.indexes:
                info["indexes"].append({
                    "field_name": index.field_name,
                    "index_name": index.index_name,
                    "params": index.params
                })
            
            return info
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {"exists": False, "error": str(e)}
    
    def list_collections(self) -> List[str]:
        """
        列出所有集合
        
        Returns:
            List[str]: 集合名称列表
        """
        if not self.connect():
            return []
            
        try:
            return utility.list_collections()
        except Exception as e:
            logger.error(f"列出集合失败: {e}")
            return []
    
    def migrate_collection(self, old_collection_name: str, 
                          new_collection_name: str = None,
                          dimension: int = 768) -> bool:
        """
        迁移集合到新的schema（支持动态字段）
        
        Args:
            old_collection_name: 旧集合名称
            new_collection_name: 新集合名称，如果为None则使用旧名称
            dimension: 向量维度
            
        Returns:
            bool: 迁移成功返回True
        """
        if not self.connect():
            return False
            
        try:
            new_collection_name = new_collection_name or old_collection_name
            
            # 检查旧集合是否存在
            if not utility.has_collection(old_collection_name):
                logger.warning(f"旧集合 {old_collection_name} 不存在")
                return False
            
            # 获取旧集合信息
            old_collection = Collection(old_collection_name)
            old_schema = old_collection.schema
            
            # 检查是否已经支持动态字段
            if old_schema.enable_dynamic_field:
                logger.info(f"集合 {old_collection_name} 已支持动态字段，无需迁移")
                return True
            
            logger.info(f"开始迁移集合 {old_collection_name} -> {new_collection_name}")
            
            # 创建新集合
            new_collection = self.create_collection(
                new_collection_name + "_new", 
                dimension, 
                drop_existing=True
            )
            
            if not new_collection:
                return False
            
            # 创建索引
            self.create_indexes(new_collection)
            
            # TODO: 这里可以添加数据迁移逻辑
            # 由于数据迁移比较复杂，建议在实际使用时根据需要实现
            
            logger.info(f"集合迁移完成: {new_collection_name}_new")
            logger.warning("注意: 数据迁移需要手动处理")
            
            return True
            
        except Exception as e:
            logger.error(f"集合迁移失败: {e}")
            return False


# 全局集合管理器实例
collection_manager = MilvusCollectionManager()
