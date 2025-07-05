"""
依赖注入提供者模块

本模块实现FastAPI依赖注入的统一管理，提供：
1. 核心服务的依赖注入
2. 数据库连接的依赖注入
3. RAG组件的依赖注入
4. 配置和环境的依赖注入
"""

from functools import lru_cache
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# 核心配置和数据库
from app.core.config import settings
from app.db.mongodb import mongodb

# RAG组件
from app.rag.interfaces import (
    IDocumentLoader,
    ITextSplitter,
    IEmbedder,
    IRetriever,
    IGenerator,
    IRagPipeline
)
from app.rag.components import (
    DocumentLoader,
    TextSplitter,
    Embedder,
    Retriever,
    Generator,
    RagPipeline
)

# IndexProcessor组件
from app.rag.processor_factory import (
    IndexProcessorFactory,
    ProcessorType,
    ProcessorConfig,
    get_processor_factory,
    create_processor
)
from app.rag.index_processor import BaseIndexProcessor

# 现有服务层（暂时保持兼容）
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.user import user_service
from app.services.document_collection_service import DocumentCollectionService

# 认证相关
from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User

import logging

logger = logging.getLogger(__name__)

# ============================================================================
# 配置依赖
# ============================================================================

def get_app_settings():
    """获取应用配置"""
    return settings

# ============================================================================
# 数据库依赖
# ============================================================================

async def get_db_session():
    """获取MongoDB数据库会话"""
    return mongodb

# ============================================================================
# RAG组件依赖
# ============================================================================

@lru_cache()
def get_document_loader() -> IDocumentLoader:
    """获取文档加载器"""
    return DocumentLoader(
        supported_formats=['.pdf', '.txt', '.md', '.doc', '.docx'],
        max_file_size=50 * 1024 * 1024  # 50MB
    )

@lru_cache()
def get_text_splitter() -> ITextSplitter:
    """获取文本分割器"""
    return TextSplitter(
        chunk_size=getattr(settings, 'DEFAULT_CHUNK_SIZE', 1000),
        chunk_overlap=getattr(settings, 'DEFAULT_CHUNK_OVERLAP', 200)
    )

@lru_cache()
def get_embedder() -> IEmbedder:
    """获取向量嵌入器"""
    return Embedder(
        model_name=getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-ada-002'),
        api_key=settings.OPENAI_API_KEY,
        api_base=getattr(settings, 'OPENAI_API_BASE', None)
    )

async def get_retriever(
    embedder: IEmbedder = Depends(get_embedder)
) -> IRetriever:
    """获取文档检索器"""
    return Retriever(
        embedder=embedder,
        collection_name="rag_documents",
        top_k=getattr(settings, 'DEFAULT_TOP_K', 5),
        similarity_threshold=getattr(settings, 'SIMILARITY_THRESHOLD', 0.7)
    )

@lru_cache()
def get_generator() -> IGenerator:
    """获取答案生成器"""
    return Generator(
        model_name=getattr(settings, 'LLM_MODEL', 'gpt-3.5-turbo'),
        api_key=settings.OPENAI_API_KEY,
        api_base=getattr(settings, 'OPENAI_API_BASE', None),
        temperature=getattr(settings, 'LLM_TEMPERATURE', 0.7),
        max_tokens=getattr(settings, 'LLM_MAX_TOKENS', 1000)
    )

async def get_rag_pipeline(
    loader: IDocumentLoader = Depends(get_document_loader),
    splitter: ITextSplitter = Depends(get_text_splitter),
    embedder: IEmbedder = Depends(get_embedder),
    retriever: IRetriever = Depends(get_retriever),
    generator: IGenerator = Depends(get_generator)
) -> IRagPipeline:
    """获取RAG流程管道"""
    return RagPipeline(
        loader=loader,
        splitter=splitter,
        embedder=embedder,
        retriever=retriever,
        generator=generator
    )

# ============================================================================
# IndexProcessor依赖注入
# ============================================================================

@lru_cache()
def get_processor_factory_instance() -> IndexProcessorFactory:
    """获取处理器工厂实例"""
    return get_processor_factory()

def get_index_processor() -> BaseIndexProcessor:
    """获取索引处理器实例（默认为父子文档处理器）

    Returns:
        BaseIndexProcessor: 索引处理器实例
    """
    factory = get_processor_factory_instance()
    return factory.get_or_create_processor(ProcessorType.PARENT_CHILD, None)

def get_parent_child_processor() -> BaseIndexProcessor:
    """获取父子文档处理器实例（便捷函数）

    Returns:
        BaseIndexProcessor: 父子文档处理器实例
    """
    return get_index_processor()

# ============================================================================
# 服务层依赖（当前实现，逐步迁移到组件化）
# ============================================================================

async def get_rag_service() -> RAGService:
    """获取RAG服务"""
    return RAGService()

async def get_llm_service() -> LLMService:
    """获取LLM服务"""
    return LLMService()

async def get_user_service():
    """获取用户服务"""
    return user_service

async def get_document_collection_service() -> DocumentCollectionService:
    """获取文档集合服务"""
    return DocumentCollectionService()

# ============================================================================
# 认证依赖（重新导出以保持一致性）
# ============================================================================

# 重新导出认证相关依赖，保持API一致性
__all__ = [
    # 配置
    "get_app_settings",

    # 数据库
    "get_db_session",

    # RAG组件
    "get_document_loader",
    "get_text_splitter",
    "get_embedder",
    "get_retriever",
    "get_generator",
    "get_rag_pipeline",

    # IndexProcessor组件
    "get_processor_factory_instance",
    "get_index_processor",
    "get_parent_child_processor",

    # 服务
    "get_rag_service",
    "get_llm_service",
    "get_user_service",
    "get_document_collection_service",

    # 认证（重新导出）
    "get_current_user",
    "get_current_active_user"
]
