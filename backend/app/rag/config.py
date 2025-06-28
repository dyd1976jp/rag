"""
RAG模块的配置文件

本模块提供RAG系统的配置，现在从主配置模块获取配置值。
保持向后兼容性，同时使用统一的配置管理。
"""
from typing import Dict, Any
from ..core.config import settings

# Milvus配置 - 从主配置模块获取
def get_milvus_config() -> Dict[str, Any]:
    """获取Milvus配置"""
    return {
        "host": settings.MILVUS_HOST,
        "port": settings.MILVUS_PORT,
        "collection_name": settings.MILVUS_COLLECTION,
        "dimension": settings.RAG_EMBEDDING_DIMENSION
    }

# 检索配置 - 从主配置模块获取
def get_retrieval_config() -> Dict[str, Any]:
    """获取检索配置"""
    return {
        "top_k": settings.RAG_TOP_K,
        "score_threshold": settings.RAG_SCORE_THRESHOLD,
        "score_threshold_enabled": settings.RAG_SCORE_THRESHOLD_ENABLED,
        "max_retries": settings.RAG_MAX_RETRIES,
        "retry_interval": settings.RAG_RETRY_INTERVAL
    }

# 文档处理配置 - 从主配置模块获取
def get_document_process_rule() -> Dict[str, Any]:
    """获取文档处理规则"""
    return {
        "rules": {
            "pre_processing_rules": [
                {"type": "remove_html", "enabled": settings.RAG_REMOVE_HTML},
                {"type": "remove_extra_spaces", "enabled": settings.RAG_REMOVE_EXTRA_SPACES},
                {"type": "remove_urls", "enabled": settings.RAG_REMOVE_URLS}
            ],
            "segmentation": {
                "separator": settings.RAG_SEPARATOR,
                "max_tokens": settings.RAG_MAX_TOKENS,
                "chunk_overlap": settings.RAG_CHUNK_OVERLAP
            }
        }
    }

# 嵌入模型配置 - 从主配置模块获取
def get_embedding_model_config() -> Dict[str, Any]:
    """获取嵌入模型配置"""
    return {
        "model_name": settings.RAG_EMBEDDING_MODEL,
        "api_base": settings.RAG_EMBEDDING_API_BASE
    }

# 向后兼容性 - 保持原有的变量名
MILVUS_CONFIG = get_milvus_config()
RETRIEVAL_CONFIG = get_retrieval_config()
DOCUMENT_PROCESS_RULE = get_document_process_rule()
EMBEDDING_MODEL_CONFIG = get_embedding_model_config()