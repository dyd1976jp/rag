import logging
import os
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from pymilvus.client.types import LoadState
from .document_processor import Document
from .custom_exceptions import (
    VectorStoreError, CollectionCreateError, CollectionLoadError, 
    IndexCreateError, SearchError, InsertError, DeleteError, QueryError
)
import numpy as np
import time
import uuid
from .models import DocumentSegment, ChildChunk
from .constants import Field, IndexType, Distance

logger = logging.getLogger(__name__)

class BaseVectorStore(ABC):
    @abstractmethod
    def create_collection(self, collection_name: str, dimension: int) -> None:
        pass
        
    @abstractmethod
    def insert(self, documents: List[Document], embeddings: List[List[float]]) -> None:
        pass
        
    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 2) -> List[Document]:
        pass
        
    @abstractmethod
    def delete(self, doc_ids: List[str]) -> None:
        pass

    @abstractmethod
    def get_by_ids(self, doc_ids: List[str]) -> List[Document]:
        pass

class MilvusVectorStore(BaseVectorStore):
    def __init__(self, 
                host: str = None, 
                port: int = None,
                flush_threshold: int = None,
                large_dataset_threshold: int = None,
                index_config: Dict[str, Any] = None):
        """
        初始化Milvus向量存储
        
        Args:
            host: Milvus服务器主机名，默认从环境变量MILVUS_HOST读取，或使用localhost
            port: Milvus服务器端口，默认从环境变量MILVUS_PORT读取，或使用19530
            flush_threshold: 执行flush操作的阈值，默认从环境变量MILVUS_FLUSH_THRESHOLD读取，或使用100
            large_dataset_threshold: 大数据集的阈值，默认从环境变量MILVUS_LARGE_DATASET_THRESHOLD读取，或使用10000
            index_config: 索引配置，默认为None
        """
        # 从环境变量读取配置
        self.host = host or os.environ.get("MILVUS_HOST", "localhost")
        self.port = port or int(os.environ.get("MILVUS_PORT", "19530"))
        self.collection: Optional[Collection] = None
        self.collection_name: Optional[str] = None
        
        # 性能相关配置
        self.flush_threshold = flush_threshold or int(os.environ.get("MILVUS_FLUSH_THRESHOLD", "100"))
        self.large_dataset_threshold = large_dataset_threshold or int(os.environ.get("MILVUS_LARGE_DATASET_THRESHOLD", "10000"))
        self.insert_buffer_size = int(os.environ.get("MILVUS_INSERT_BUFFER_SIZE", "1000"))
        
        # 索引配置
        self.index_config = index_config or {
            # 小数据集使用FLAT索引
            "small": {
                "index_type": "FLAT",
                "metric_type": "L2",
                "params": {}
            },
            # 中等数据集使用IVF_FLAT索引
            "medium": {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {
                    "nlist": 1024
                }
            },
            # 大数据集使用IVF_SQ8索引（更省内存）
            "large": {
                "index_type": "IVF_SQ8",
                "metric_type": "L2",
                "params": {
                    "nlist": 4096
                }
            }
        }
        
        # 连接Milvus
        self._connect()
        
        # 追踪索引状态，避免重复检查
        self._indexed_collections = set()
        self._collection_info_cache = {}
        
        logger.info(f"初始化Milvus向量存储: 服务器={self.host}:{self.port}")
        logger.info(f"性能配置: flush阈值={self.flush_threshold}, 大数据集阈值={self.large_dataset_threshold}")
        
    def _connect(self):
        """连接到Milvus服务器"""
        try:
            # 使用Docker中Milvus的连接方式
            connections.connect(host=self.host, port=str(self.port))
            logger.info(f"成功连接到Milvus服务器: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"连接Milvus服务器失败: {e}")
            raise

    def _check_connection(self):
        """检查Milvus连接状态"""
        try:
            # 检查连接是否存在
            if not connections.has_connection("default"):
                logger.warning("Milvus连接不存在，尝试重新连接")
                self._connect()

            # 简单的连接测试 - 列出集合
            utility.list_collections()
            logger.debug("Milvus连接检查通过")
            return True
        except Exception as e:
            logger.error(f"Milvus连接检查失败: {str(e)}")
            return False
    
    def _get_index_config(self, row_count: int) -> Dict[str, Any]:
        """根据数据量选择合适的索引配置"""
        # 小数据集 - 使用FLAT索引（精确搜索）
        if row_count < 10000:
            config = self.index_config["small"]
            logger.info(f"使用小数据集索引配置: {config['index_type']}")
            return config
        # 中等数据集 - 使用IVF_FLAT索引（平衡搜索速度和精度）
        elif row_count < 100000:
            config = self.index_config["medium"]
            # 动态调整nlist参数
            config["params"]["nlist"] = min(4096, max(128, row_count // 100))
            logger.info(f"使用中等数据集索引配置: {config['index_type']}, nlist={config['params']['nlist']}")
            return config
        # 大数据集 - 使用IVF_SQ8索引（更高的搜索速度，更低的内存使用，稍微牺牲精度）
        else:
            config = self.index_config["large"]
            # 动态调整nlist参数
            config["params"]["nlist"] = min(16384, max(4096, row_count // 1000))
            logger.info(f"使用大数据集索引配置: {config['index_type']}, nlist={config['params']['nlist']}")
            return config
            
    def _ensure_index(self, collection: Collection, field_name: str = "vector"):
        """确保集合在指定字段上有索引，如果没有则创建。"""
        # 如果已经检查过索引状态，则跳过
        collection_key = f"{collection.name}:{field_name}"
        if collection_key in self._indexed_collections:
            return
            
        if not collection.has_index(field_name=field_name):
            logger.info(f"集合 {collection.name} 在字段 '{field_name}' 上没有索引，正在创建索引...")
            
            # 获取集合中的实体数量，根据数据量选择合适的索引类型和参数
            row_count = collection.num_entities
            
            # 选择合适的索引配置
            index_params = self._get_index_config(row_count)
            
            try:
                # 创建索引前先异步将集合释放以节省资源
                if utility.load_state(collection.name, using="default") == LoadState.Loaded:
                    collection.release()
                    logger.info(f"索引创建前释放集合 {collection.name} 以节省资源")
                
                # 创建索引
                collection.create_index(field_name, index_params)
                logger.info(f"集合 {collection.name} 在字段 '{field_name}' 上的索引已创建.")
                utility.wait_for_index_building_complete(collection.name, field_name, using="default")
                logger.info(f"集合 {collection.name} 在字段 '{field_name}' 上的索引构建完成.")
                
                # 将索引状态记录到缓存中
                self._indexed_collections.add(collection_key)
            except Exception as e:
                logger.error(f"为集合 {collection.name} 创建索引失败: {e}")
                raise
        else:
            logger.info(f"集合 {collection.name} 在字段 '{field_name}' 上已存在索引.")
            # 将索引状态记录到缓存中
            self._indexed_collections.add(collection_key)
    
    def _get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息，优先从缓存读取"""
        if collection_name in self._collection_info_cache:
            return self._collection_info_cache[collection_name]
        
        info = {
            "exists": utility.has_collection(collection_name, using="default"),
            "row_count": 0,
            "loaded": False
        }
        
        if info["exists"]:
            collection = Collection(collection_name)
            info["row_count"] = collection.num_entities
            info["loaded"] = utility.load_state(collection_name, using="default") == LoadState.Loaded
            info["collection"] = collection
        
        # 缓存信息
        self._collection_info_cache[collection_name] = info
        return info

    def create_collection(self, collection_name: str, dimension: int = 768):
        """创建集合，包含向量和文本索引"""
        if utility.has_collection(collection_name):
            self.collection = Collection(collection_name)
            self.collection_name = collection_name
            logger.info(f"集合 '{collection_name}' 已存在，将使用现有集合")
            return

        try:
            # 向量参数配置
            vectors_config = {
                "size": dimension,                
                "distance": os.environ.get("VECTOR_DISTANCE", Distance.COSINE),  
            }

            # 创建字段定义
            fields = [
                FieldSchema(
                    name=Field.PRIMARY_KEY.value,
                    dtype=DataType.VARCHAR,
                    is_primary=True,
                    auto_id=False,
                    max_length=100
                ),
                FieldSchema(
                    name=Field.VECTOR.value,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dimension
                ),
                FieldSchema(
                    name=Field.CONTENT_KEY.value,
                    dtype=DataType.VARCHAR,
                    max_length=65535
                ),
                FieldSchema(
                    name=Field.METADATA_KEY.value,
                    dtype=DataType.JSON
                ),
                FieldSchema(
                    name=Field.GROUP_KEY.value,
                    dtype=DataType.VARCHAR,
                    max_length=100
                ),
                FieldSchema(
                    name=Field.SPARSE_VECTOR.value,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dimension
                )
            ]

            # 创建schema
            schema = CollectionSchema(
                fields=fields,
                description="Document vectors with text and metadata"
            )

            # 创建集合
            self.collection = Collection(
                name=collection_name,
                schema=schema
            )
            self.collection_name = collection_name

            # HNSW索引配置
            hnsw_config = {
                "m": 16,                         # 图的最大出度
                "payload_m": 16,                 # payload图的最大出度
                "ef_construct": 100,             # 构建时的搜索深度
                "full_scan_threshold": 10000,    # 全扫描阈值
                "max_indexing_threads": 0,       # 索引线程数
                "on_disk": False,               # 是否存储在磁盘上
            }

            # 创建向量索引
            self.collection.create_index(
                field_name=Field.VECTOR.value,
                index_params={
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024},
                    "metric_type": "L2"
                }
            )

            # 创建稀疏向量索引
            self.collection.create_index(
                field_name=Field.SPARSE_VECTOR.value,
                index_params={
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024},
                    "metric_type": "L2"
                }
            )

            logger.info(f"集合 {collection_name} 创建成功，包含向量索引")
            return True

        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            raise

    def _ensure_collection_loaded(self, collection: Collection):
        """确保集合已加载到内存中"""
        try:
            load_state = utility.load_state(collection.name, using="default")
            if load_state != LoadState.Loaded:
                logger.info(f"集合 {collection.name} 未加载，正在加载...")
                collection.load()
                logger.info(f"集合 {collection.name} 已加载.")
                
                # 更新缓存
                if collection.name in self._collection_info_cache:
                    self._collection_info_cache[collection.name]["loaded"] = True
            else:
                logger.info(f"集合 {collection.name} 已加载.")
        except Exception as e:
            logger.error(f"加载集合 {collection.name} 失败: {e}")
            raise
            
    def insert(self, documents: List[Document], vectors: List[List[float]]):
        """插入文档，包含向量和文本数据"""
        try:
            if not documents or not vectors:
                return

            # 准备数据
            data = []
            for doc, vector in zip(documents, vectors):
                point = {
                    Field.PRIMARY_KEY.value: doc.metadata.get("doc_id", str(uuid.uuid4())),
                    Field.VECTOR.value: vector,
                    Field.CONTENT_KEY.value: doc.page_content,
                    Field.METADATA_KEY.value: doc.metadata,
                    Field.GROUP_KEY.value: doc.metadata.get("group_id", ""),
                    Field.SPARSE_VECTOR.value: vector  # 这里简化处理，实际应该是不同的向量
                }
                data.append(point)

            # 执行插入
            self.collection.insert(data)
            logger.info(f"成功插入 {len(documents)} 条数据")

        except Exception as e:
            logger.error(f"插入数据失败: {str(e)}")
            raise
        
    def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 2,
        score_threshold: float = 0.0,
        dataset_id: Optional[str] = None
    ) -> List[Document]:
        """搜索相似向量"""
        if not self.collection:
            logger.error("集合未初始化，无法执行搜索")
            raise SearchError("集合未初始化，无法执行搜索")
        
        try:
            # 确保集合已加载
            self._ensure_collection_loaded(self.collection)
            
            search_params = {
                "metric_type": "L2",  # 使用L2距离
                "params": {"nprobe": min(50, max(10, top_k * 2))}  # 动态调整nprobe
            }
            
            # 添加过滤条件（如果指定了数据集ID）
            expr = None
            if dataset_id:
                expr = f'metadata["dataset_id"] == "{dataset_id}"'
                logger.info(f"添加过滤条件: {expr}")
            
            logger.info(f"正在集合 {self.collection.name} 中执行搜索, top_k={top_k}")
            start_time = time.time()
            
            # 执行向量搜索
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=[Field.CONTENT_KEY.value, Field.METADATA_KEY.value]
            )
            
            search_time = time.time() - start_time
            logger.info(f"搜索完成，耗时 {search_time:.3f} 秒")
            
            # 处理搜索结果
            search_results = []
            for hits in results:
                for hit in hits:
                    entity = hit.entity
                    metadata = entity.get(Field.METADATA_KEY.value, {})
                    page_content = entity.get(Field.CONTENT_KEY.value, "")
                    metadata['score'] = float(hit.distance)
                    
                    doc = Document(page_content=page_content, metadata=metadata)
                    search_results.append(doc)
            
            # 如果启用了分数阈值，过滤结果
            if score_threshold > 0:
                filtered_results = []
                for doc in search_results:
                    score = doc.metadata.get('score', 0)
                    if score >= score_threshold:
                        filtered_results.append(doc)
                search_results = filtered_results
                logger.info(f"应用分数阈值 {score_threshold}，过滤后剩余 {len(search_results)} 个结果")
            
            logger.info(f"搜索完成，返回 {len(search_results)} 个结果")
            return search_results
            
        except Exception as e:
            logger.error(f"在集合 {self.collection.name if self.collection else 'None'} 中搜索失败: {e}")
            raise SearchError(f"向量搜索失败: {str(e)}")
            
    def get_by_id(self, doc_id: str) -> Optional[Document]:
        """通过ID获取文档"""
        if not self.collection:
            logger.error("集合未初始化，无法执行查询")
            raise ValueError("Collection not initialized")
            
        # 确保集合已加载
        self._ensure_collection_loaded(self.collection)
            
        try:
            result = self.collection.query(
                expr=f'{Field.PRIMARY_KEY.value} == "{doc_id}"',
                output_fields=[Field.CONTENT_KEY.value, Field.METADATA_KEY.value]
            )
            
            if not result:
                return None
                
            res = result[0]
            metadata = res.get(Field.METADATA_KEY.value, {})
            content = res.get(Field.CONTENT_KEY.value, "")
            
            document = Document(
                page_content=content,
                metadata=metadata
            )
            
            return document
        except Exception as e:
            logger.error(f"查询文档失败: {e}")
            raise
            
    def delete(self, doc_ids: List[str]):
        """删除文档"""
        if not doc_ids:
            return
        
        if self.collection is None:
            if self.collection_name:
                self.collection = Collection(self.collection_name)
            else:
                logger.error("集合未初始化，无法执行删除")
                raise ValueError("Collection not initialized")

        try:
            # 对于大量ID，分批删除
            if len(doc_ids) > 1000:
                total_count = len(doc_ids)
                deleted_count = 0
                batch_size = 1000
                
                for i in range(0, total_count, batch_size):
                    end_idx = min(i + batch_size, total_count)
                    batch_ids = doc_ids[i:end_idx]
                    
                    formatted_ids = ", ".join([f'"{_id}"' for _id in batch_ids])
                    expr = f'id in [{formatted_ids}]'
                    
                    logger.info(f"正在删除批次 {i//batch_size + 1}/{(total_count+batch_size-1)//batch_size}，包含 {len(batch_ids)} 个文档")
                    self.collection.delete(expr)
                    deleted_count += len(batch_ids)
                    
                    # 每处理完一批数据，报告进度
                    logger.info(f"已删除 {deleted_count}/{total_count} 个文档 ({deleted_count/total_count*100:.1f}%)")
                
                # 更新缓存中的行数
                if self.collection.name in self._collection_info_cache:
                    self._collection_info_cache[self.collection.name]["row_count"] -= deleted_count
                
                logger.info(f"成功删除了 {deleted_count} 个文档")
            else:
                # 构造删除表达式
                formatted_ids = ", ".join([f'"{_id}"' for _id in doc_ids])
                expr = f'id in [{formatted_ids}]'
                
                # 执行删除操作
                self.collection.delete(expr)
                
                # 更新缓存中的行数
                if self.collection.name in self._collection_info_cache:
                    self._collection_info_cache[self.collection.name]["row_count"] -= len(doc_ids)
                
                logger.info(f"已删除 {len(doc_ids)} 个文档")
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise
            
    def get_by_ids(self, doc_ids: List[str]) -> List[Document]:
        """通过ID列表获取多个文档"""
        if not self.collection:
            logger.error("集合未初始化，无法执行查询")
            raise QueryError("Collection not initialized")
        
        if not doc_ids:
            return []

        self._ensure_collection_loaded(self.collection)

        try:
            ids_str = ", ".join([f'"{doc_id}"' for doc_id in doc_ids])
            expr = f'{Field.PRIMARY_KEY.value} in [{ids_str}]'
            
            output_fields = [Field.CONTENT_KEY.value, Field.METADATA_KEY.value]
            
            results = self.collection.query(
                expr=expr,
                output_fields=output_fields
            )

            documents = []
            for res in results:
                page_content = res.get(Field.CONTENT_KEY.value, "")
                metadata = res.get(Field.METADATA_KEY.value, {})
                doc = Document(page_content=page_content, metadata=metadata)
                documents.append(doc)

            return documents
        except Exception as e:
            logger.error(f"通过ID列表查询文档失败: {e}")
            raise QueryError(f"Failed to query documents by IDs: {e}")
            
    def search(self, query_embedding: List[float], top_k: int = 2) -> List[Document]:
        """搜索相似向量"""
        return self.search_by_vector(query_embedding, top_k)
        
    def get_stats(self):
        """获取集合统计信息"""
        try:
            collection = self.get_collection()
            if collection is None:
                raise ValueError("集合未初始化")
                
            stats = {
                "collection_name": collection.name,
                "row_count": collection.num_entities,
                "schema": collection.schema,
                "index_info": {}
            }
            
            # 获取索引信息
            indexes = collection.indexes
            if indexes:
                stats["index_info"] = indexes
                
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    def insert_chunks(self, chunks: List[ChildChunk]):
        """插入子块向量"""
        if not chunks:
            return
            
        try:
            # 准备数据
            chunk_ids = [chunk.metadata["chunk_id"] for chunk in chunks]
            segment_ids = [chunk.segment_id for chunk in chunks]
            vectors = [chunk.vector for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            
            # 插入数据
            entities = [
                chunk_ids,
                segment_ids,
                vectors,
                metadatas
            ]
            
            self.collection.insert(entities)
            logger.info(f"成功插入 {len(chunks)} 个子块向量")
            
        except Exception as e:
            logger.error(f"插入向量失败: {e}")
            raise VectorStoreError(f"插入向量失败: {str(e)}")
            
    def search(self, query_vector: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            # 确保集合已加载
            if not self.collection:
                raise VectorStoreError("集合未初始化")
                
            # 执行搜索
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": min(50, max(10, top_k * 2))}
            }
            
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["segment_id", "metadata"]
            )
            
            # 处理结果
            search_results = []
            for hits in results:
                for hit in hits:
                    result = {
                        "chunk_id": hit.id,
                        "segment_id": hit.entity.get("segment_id"),
                        "metadata": hit.entity.get("metadata", {}),
                        "score": float(hit.distance)
                    }
                    search_results.append(result)
                    
            return search_results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise VectorStoreError(f"搜索失败: {str(e)}")
            
    def delete_by_segment_id(self, segment_id: str):
        """删除指定父块ID的所有子块"""
        try:
            self.collection.delete(f'segment_id == "{segment_id}"')
            logger.info(f"成功删除父块 {segment_id} 的所有子块")
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            raise VectorStoreError(f"删除向量失败: {str(e)}")

    def get_collection(self):
        """获取当前集合"""
        return self.collection 