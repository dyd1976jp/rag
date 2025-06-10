"""
RAG模块初始化文件
"""
import os
import logging
from .config import MILVUS_CONFIG, EMBEDDING_MODEL_CONFIG, RETRIEVAL_CONFIG, DOCUMENT_PROCESS_RULE
from .embedding_model import EmbeddingModel
from .vector_store import MilvusVectorStore
from .retrieval_service import RetrievalService
from .document_processor import DocumentProcessor
from .document_splitter import (
    DocumentSplitter,
    QADocumentSplitter,
    ParentChildDocumentSplitter,
    Rule,
    SplitMode
)
from .text_splitter import FixedRecursiveCharacterTextSplitter
from .pdf_processor import PDFProcessor
from .cache_service import CacheService
from app.db.mongodb import mongodb
from app.db.document_store import DocumentStore
from .models import Document, DocumentSegment, ChildDocument
from .database import MongoDBManager

# 配置日志
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化各个组件，以便在出错时能明确提示哪个组件出了问题
embedding_model = None
vector_store = None
retrieval_service = None
document_processor = None
document_splitter = None
pdf_processor = None
cache_service = None

# 创建全局检索服务实例
retrieval_service = None

# 创建全局文档处理器实例
document_processor = None

# 创建全局文档分割器实例
document_splitter = None

# 创建全局PDF处理器实例
pdf_processor = None

async def initialize_rag():
    global embedding_model, vector_store, retrieval_service, document_processor, document_splitter, pdf_processor, cache_service
    
    # 创建全局嵌入模型实例
    try:
        embedding_model = EmbeddingModel()
        logger.info("嵌入模型初始化成功")
    except Exception as e:
        logger.error(f"嵌入模型初始化失败: {str(e)}")
        logger.error("请确保嵌入模型服务已启动并可访问")

    # 创建全局向量存储实例
    try:
        vector_store = MilvusVectorStore(
            host=os.environ.get("MILVUS_HOST", "localhost"),
            port=int(os.environ.get("MILVUS_PORT", "19530")),
            flush_threshold=int(os.environ.get("MILVUS_FLUSH_THRESHOLD", "100")),
            large_dataset_threshold=int(os.environ.get("MILVUS_LARGE_DATASET_THRESHOLD", "10000"))
        )
        logger.info("向量存储初始化成功")
    except Exception as e:
        logger.error(f"向量存储初始化失败: {str(e)}")
        logger.error("请确保Milvus服务已启动。RAG功能需要Milvus向量数据库。")
        logger.error("可以使用Docker运行Milvus: docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone")

    # 创建全局缓存服务实例
    use_cache = os.environ.get("USE_CACHE", "false").lower() == "true"
    if use_cache:
        try:
            cache_service = CacheService()
            if cache_service.enabled:
                logger.info("缓存服务已启用")
            else:
                logger.warning("Redis连接失败，缓存服务已禁用")
                cache_service = None
        except Exception as e:
            logger.warning(f"初始化缓存服务失败: {str(e)}")
            cache_service = None
    else:
        logger.info("缓存服务已在配置中禁用")
        cache_service = None

    # 创建全局检索服务实例
    if embedding_model is not None and vector_store is not None:
        try:
            from app.db.mongodb import mongodb
            from app.db.document_store import DocumentStore
            from app.rag.retrieval_service import RetrievalService
            from app.rag.constants import RETRIEVAL_CONFIG
            
            document_store = DocumentStore(mongodb.db)
            
            retrieval_service = RetrievalService(
                vector_store=vector_store,
                document_store=document_store,
                embedding_model=embedding_model,
                retrieval_config=RETRIEVAL_CONFIG,
                cache_service=cache_service
            )
            logger.info("检索服务初始化成功")
        except Exception as e:
            logger.error(f"检索服务初始化失败: {str(e)}")
            retrieval_service = None
    else:
        logger.warning("嵌入模型或向量存储未初始化，检索服务将不可用")
        retrieval_service = None

    # 创建全局文档处理器实例
    try:
        document_processor = DocumentProcessor()
        logger.info("文档处理器初始化成功")
    except Exception as e:
        logger.error(f"文档处理器初始化失败: {str(e)}")

    # 创建全局文档分割器实例
    try:
        document_splitter = DocumentSplitter()
        logger.info("文档分割器初始化成功")
    except Exception as e:
        logger.error(f"文档分割器初始化失败: {str(e)}")

    # 创建全局PDF处理器实例
    try:
        pdf_processor = PDFProcessor()
        logger.info("PDF处理器初始化成功")
    except Exception as e:
        logger.error(f"PDF处理器初始化失败: {str(e)}")

    # 检查RAG功能是否可用
    if None in [embedding_model, vector_store, retrieval_service, document_processor, document_splitter, pdf_processor]:
        logger.warning("部分RAG组件初始化失败，RAG功能将不可用或受限")
    else:
        logger.info("RAG模块初始化成功，所有功能可用")

__all__ = [
    'Document',
    'DocumentSegment',
    'ChildDocument',
    'DocumentSplitter',
    'QADocumentSplitter',
    'ParentChildDocumentSplitter',
    'Rule',
    'SplitMode',
    'FixedRecursiveCharacterTextSplitter',
    'MongoDBManager'
]
