from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pathlib import Path
from langchain.schema import Document
from app.rag.models import Dataset
from app.rag.embedding_model import EmbeddingModel
from app.rag.vector_store import MilvusVectorStore, BaseVectorStore
from app.rag.pdf_processor import process_pdf
import hashlib
import os

class VectorType(str, Enum):
    """向量数据库类型枚举"""
    CHROMA = "chroma"
    MILVUS = "milvus"
    PGVECTOR = "pgvector"
    QDRANT = "qdrant"
    ELASTICSEARCH = "elasticsearch"
    WEAVIATE = "weaviate"

class Vector:
    """向量存储核心类"""
    
    def __init__(self, dataset: Dataset, attributes: Optional[list] = None):
        """初始化向量存储实例
        
        Args:
            dataset: 数据集实例
            attributes: 元数据属性列表，默认包含doc_id、dataset_id、document_id、doc_hash
        """
        self._dataset = dataset
        self._embeddings = self._get_embeddings()  # 获取embedding模型
        self._attributes = attributes or ["doc_id", "dataset_id", "document_id", "doc_hash"]
        self._vector_processor = self._init_vector()  # 初始化向量存储

    def _get_embeddings(self) -> EmbeddingModel:
        """获取embedding模型实例"""
        model_name = os.environ.get("EMBEDDING_MODEL")
        api_base = os.environ.get("EMBEDDING_API_BASE")
        return EmbeddingModel(model_name=model_name, api_base=api_base)

    def _init_vector(self) -> BaseVectorStore:
        """初始化向量存储处理器"""
        # 从环境变量获取向量存储类型，默认使用Milvus
        vector_type = os.environ.get("VECTOR_STORE_TYPE", "milvus")
        
        if vector_type.lower() == "milvus":
            host = os.environ.get("MILVUS_HOST")
            port = int(os.environ.get("MILVUS_PORT", "19530"))
            return MilvusVectorStore(host=host, port=port)
        else:
            raise ValueError(f"不支持的向量存储类型: {vector_type}")

    def _filter_duplicate_texts(self, documents: List[Document]) -> List[Document]:
        """文档去重处理
        
        Args:
            documents: 待处理的文档列表
            
        Returns:
            去重后的文档列表
        """
        unique_docs = {}
        for doc in documents:
            # 计算文档内容的hash值
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            
            # 如果文档没有metadata，初始化为空字典
            if not doc.metadata:
                doc.metadata = {}
                
            # 添加hash值到metadata
            doc.metadata["doc_hash"] = content_hash
            
            # 使用content_hash作为唯一标识
            unique_docs[content_hash] = doc
            
        return list(unique_docs.values())

    def process_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Document:
        """处理文件（支持PDF和文本文件）
        
        Args:
            file_path: 文件路径
            metadata: 可选的元数据

        Returns:
            Document: 处理后的文档对象
        """
        if metadata is None:
            metadata = {}

        # 确保必要的元数据字段存在
        metadata.update({
            "dataset_id": self._dataset.id,
            "document_id": metadata.get("document_id", str(Path(file_path).stem)),
            "file_path": file_path,
            "file_type": Path(file_path).suffix.lower()
        })

        # 根据文件类型处理
        if file_path.lower().endswith('.pdf'):
            return process_pdf(file_path, metadata)
        else:
            # 处理文本文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return Document(page_content=content, metadata=metadata)

    def create(self, files: Optional[Union[str, List[str]]] = None, texts: Optional[list] = None, **kwargs):
        """创建向量存储
        
        Args:
            files: 单个文件路径或文件路径列表
            texts: 文档列表，每个文档包含内容和元数据
            **kwargs: 额外参数
        """
        documents = []
        
        # 处理文件
        if files:
            if isinstance(files, str):
                files = [files]
            for file_path in files:
                doc = self.process_file(file_path)
                documents.append(doc)
        
        # 处理文本文档
        if texts:
            documents.extend(texts)
            
        if documents:
            # 为文档生成向量嵌入
            embeddings = self._embeddings.embed_documents(
                [document.page_content for document in documents]
            )
            # 存储文档及其向量
            self._vector_processor.create(texts=documents, embeddings=embeddings, **kwargs)

    def add_texts(self, documents: List[Document], **kwargs):
        """添加文档到向量存储
        
        Args:
            documents: 文档列表
            **kwargs: 额外参数，支持duplicate_check等选项
        """
        # 去重检查
        if kwargs.get("duplicate_check", False):
            documents = self._filter_duplicate_texts(documents)
        
        # 确保所有必要的元数据字段都存在
        for doc in documents:
            if not doc.metadata:
                doc.metadata = {}
            
            # 设置默认元数据
            if "dataset_id" not in doc.metadata:
                doc.metadata["dataset_id"] = self._dataset.id
            if "doc_id" not in doc.metadata:
                doc.metadata["doc_id"] = doc.metadata.get("document_id", None)
            if "doc_hash" not in doc.metadata:
                content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
                doc.metadata["doc_hash"] = content_hash
        
        # 生成文档向量并存储
        embeddings = self._embeddings.embed_documents(
            [document.page_content for document in documents]
        )
        self._vector_processor.insert(texts=documents, embeddings=embeddings, **kwargs)