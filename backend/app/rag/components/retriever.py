"""
文档检索器组件

实现基于向量相似度的文档检索功能。
实现IRetriever接口，提供统一的文档检索功能。
"""

import logging
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, utility

from app.rag.interfaces import BaseRetriever, DocumentChunk, RetrievalResult, IEmbedder
from app.core.config import settings

logger = logging.getLogger(__name__)

class Retriever(BaseRetriever):
    """文档检索器实现"""
    
    def __init__(
        self,
        embedder: IEmbedder,
        collection_name: str = "rag_documents",
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        host: str = "localhost",
        port: str = "19530"
    ):
        """
        初始化文档检索器
        
        Args:
            embedder: 向量嵌入器
            collection_name: Milvus集合名称
            top_k: 默认返回结果数量
            similarity_threshold: 相似度阈值
            host: Milvus主机地址
            port: Milvus端口
        """
        self.embedder = embedder
        self.collection_name = collection_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.host = host
        self.port = port
        
        # 连接到Milvus
        self._connect_milvus()
        
        # 初始化集合
        self._init_collection()
    
    def _connect_milvus(self):
        """连接到Milvus"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"成功连接到Milvus: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"连接Milvus失败: {e}")
            raise
    
    def _init_collection(self):
        """初始化Milvus集合"""
        try:
            from pymilvus import FieldSchema, CollectionSchema, DataType
            
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"使用现有集合: {self.collection_name}")
            else:
                # 创建集合schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedder.dimension),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535)
                ]
                
                schema = CollectionSchema(fields, "RAG文档集合")
                self.collection = Collection(self.collection_name, schema)
                
                # 创建索引
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                self.collection.create_index("vector", index_params)
                
                logger.info(f"创建新集合: {self.collection_name}")
            
            # 加载集合
            self.collection.load()
            
        except Exception as e:
            logger.error(f"初始化Milvus集合失败: {e}")
            raise
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        if not query.strip():
            return []
        
        top_k = top_k or self.top_k
        
        try:
            # 向量化查询
            query_vector = await self.embedder.embed_text(query)
            
            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 构建过滤表达式
            expr = None
            if filters:
                expr_parts = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        expr_parts.append(f'metadata like "%{key}:{value}%"')
                    elif isinstance(value, (int, float)):
                        expr_parts.append(f'metadata like "%{key}:{value}%"')
                
                if expr_parts:
                    expr = " and ".join(expr_parts)
            
            # 执行搜索
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["content", "metadata"]
            )
            
            # 转换结果
            retrieval_results = []
            for hit in results[0]:
                score = float(hit.score)
                
                # 应用相似度阈值
                if score >= self.similarity_threshold:
                    result = RetrievalResult(
                        content=hit.entity.get("content", ""),
                        score=score,
                        metadata=self._parse_metadata(hit.entity.get("metadata", "{}")),
                        chunk_id=hit.id
                    )
                    retrieval_results.append(result)
            
            logger.info(f"检索到 {len(retrieval_results)} 个相关文档")
            return retrieval_results
            
        except Exception as e:
            logger.error(f"文档检索失败: {e}")
            return []
    
    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        添加文档到检索索引
        
        Args:
            chunks: 要添加的文档块列表
            
        Returns:
            bool: 是否成功
        """
        if not chunks:
            return True
        
        try:
            # 准备数据
            ids = []
            vectors = []
            contents = []
            metadatas = []
            
            for chunk in chunks:
                # 如果没有向量，先生成向量
                if not chunk.vector:
                    chunk.vector = await self.embedder.embed_text(chunk.content)
                
                ids.append(chunk.chunk_id)
                vectors.append(chunk.vector)
                contents.append(chunk.content)
                metadatas.append(self._serialize_metadata(chunk.metadata))
            
            # 插入数据
            entities = [ids, vectors, contents, metadatas]
            self.collection.insert(entities)
            
            # 刷新集合
            self.collection.flush()
            
            logger.info(f"成功添加 {len(chunks)} 个文档块到索引")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到索引失败: {e}")
            return False
    
    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """序列化元数据"""
        import json
        try:
            return json.dumps(metadata, ensure_ascii=False)
        except Exception:
            return "{}"
    
    def _parse_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """解析元数据"""
        import json
        try:
            return json.loads(metadata_str)
        except Exception:
            return {}
    
    async def delete_documents(self, chunk_ids: List[str]) -> bool:
        """
        删除文档
        
        Args:
            chunk_ids: 要删除的文档块ID列表
            
        Returns:
            bool: 是否成功
        """
        if not chunk_ids:
            return True
        
        try:
            # 构建删除表达式
            ids_str = "', '".join(chunk_ids)
            expr = f"id in ['{ids_str}']"
            
            # 执行删除
            self.collection.delete(expr)
            self.collection.flush()
            
            logger.info(f"成功删除 {len(chunk_ids)} 个文档块")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            stats = self.collection.get_stats()
            return {
                "total_documents": stats.get("row_count", 0),
                "collection_name": self.collection_name,
                "dimension": self.embedder.dimension
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {}
    
    def set_similarity_threshold(self, threshold: float) -> None:
        """设置相似度阈值"""
        self.similarity_threshold = max(0.0, min(1.0, threshold))
    
    def set_top_k(self, top_k: int) -> None:
        """设置默认返回结果数量"""
        self.top_k = max(1, top_k)
