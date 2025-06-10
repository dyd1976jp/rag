import os
import logging
from typing import Optional, List, Dict, Any
from langchain_community.vectorstores import Milvus
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType

logger = logging.getLogger(__name__)

# Milvus配置
MILVUS_HOST = os.environ.get("MILVUS_HOST", "localhost")
MILVUS_PORT = os.environ.get("MILVUS_PORT", "19530")
COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "rag_documents")
VECTOR_DIM = 768  # nomic-embed-text-v1.5 模型的向量维度

_vector_store: Optional[Milvus] = None

def create_collection() -> None:
    """创建Milvus集合"""
    try:
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        # 创建集合模式
        schema = CollectionSchema(fields=fields, description="文档向量存储")
        
        # 创建集合
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        
        # 创建索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
        collection.create_index(field_name="vector", index_params=index_params)
        collection.load()
        
        logger.info(f"成功创建集合: {COLLECTION_NAME}")
    except Exception as e:
        logger.error(f"创建集合失败: {str(e)}")
        raise

def get_vector_store(embedding_model: Embeddings) -> Milvus:
    """获取或创建向量存储实例"""
    global _vector_store
    
    if _vector_store is None:
        try:
            # 连接到Milvus
            connections.connect(
                alias="default",
                host=MILVUS_HOST,
                port=MILVUS_PORT
            )
            
            # 如果集合不存在，创建它
            if not utility.has_collection(COLLECTION_NAME):
                create_collection()
            
            # 初始化向量存储
            _vector_store = Milvus(
                embedding_function=embedding_model,
                collection_name=COLLECTION_NAME,
                connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
                text_field="content",
                vector_field="vector",
                primary_field="id",
                metadata_field="metadata"
            )
            
            logger.info("向量存储初始化成功")
        except Exception as e:
            logger.error(f"初始化向量存储失败: {str(e)}")
            raise
            
    return _vector_store

def clear() -> None:
    """清理向量存储"""
    try:
        # 确保连接存在
        connections.connect(
            alias="default",
            host=MILVUS_HOST,
            port=MILVUS_PORT
        )
        
        if utility.has_collection(COLLECTION_NAME):
            utility.drop_collection(COLLECTION_NAME)
            logger.info(f"集合 {COLLECTION_NAME} 已删除")
    except Exception as e:
        logger.error(f"删除集合失败: {str(e)}")
        raise

def add_documents(documents: List[Document], embeddings: List[List[float]]) -> bool:
    """添加文档到向量存储"""
    try:
        # 获取集合
        collection = Collection(COLLECTION_NAME)
        
        # 准备插入数据
        data = []
        for doc, embedding in zip(documents, embeddings):
            data_point = {
                "id": doc.metadata.get("doc_id", ""),
                "content": doc.page_content,
                "vector": embedding,
                "metadata": doc.metadata
            }
            data.append(data_point)
            
        # 执行插入
        collection.insert(data)
        logger.info(f"成功插入 {len(documents)} 条文档")
        return True
    except Exception as e:
        logger.error(f"插入文档失败: {str(e)}")
        return False

def search_similar(query_embedding: List[float], top_k: int = 2) -> List[Document]:
    """搜索相似文档"""
    try:
        # 获取集合
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        # 执行搜索
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        results = collection.search(
            data=[query_embedding],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["content", "metadata"]
        )
        
        # 处理结果
        documents = []
        for hits in results:
            for hit in hits:
                doc = Document(
                    page_content=hit.entity.get("content", ""),
                    metadata=hit.entity.get("metadata", {})
                )
                documents.append(doc)
                
        return documents
    except Exception as e:
        logger.error(f"搜索文档失败: {str(e)}")
        return [] 