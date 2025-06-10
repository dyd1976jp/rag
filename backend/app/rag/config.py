"""
RAG模块的配置文件
"""
from typing import Dict, Any
import os

# Milvus配置
MILVUS_CONFIG = {
    "host": "localhost",
    "port": 19530,
    "collection_name": "rag_documents",
    "dimension": 768
}

# 检索配置
RETRIEVAL_CONFIG = {
    "top_k": 3,
    "score_threshold": 0.0,
    "score_threshold_enabled": False,
    "max_retries": 3,
    "retry_interval": 5
}

# 文档处理配置
DOCUMENT_PROCESS_RULE = {
    "rules": {
        "pre_processing_rules": [
            {"type": "remove_html", "enabled": True},
            {"type": "remove_extra_spaces", "enabled": True},
            {"type": "remove_urls", "enabled": True}
        ],
        "segmentation": {
            "separator": "\n\n",
            "max_tokens": 512,
            "chunk_overlap": 100
        }
    }
}

# 嵌入模型配置
EMBEDDING_MODEL_CONFIG = {
    "model_name": "text-embedding-nomic-embed-text-v1.5",
    "api_base": "http://192.168.1.30:1234"  # 根据您的环境修改
} 