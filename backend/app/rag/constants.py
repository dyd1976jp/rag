"""
RAG 系统常量定义
"""

from enum import Enum
from ..core.paths import (
    CACHE_DIR,
    SPLITTER_CACHE_DIR
)

# 默认集合名称
DEFAULT_COLLECTION_NAME = "rag_documents"

# 检索配置
RETRIEVAL_CONFIG = {
    "top_k": 3,                    # 默认返回结果数量
    "score_threshold": 0.0,        # 分数阈值
    "score_threshold_enabled": False,  # 是否启用分数阈值
    "max_retries": 3,             # 最大重试次数
    "retry_interval": 5,          # 重试间隔（秒）
    "reranking_model": {
        "enabled": False,         # 是否启用重排序
        "model": "default"        # 重排序模型
    }
}

# 向量存储配置
VECTOR_STORE_CONFIG = {
    "flush_threshold": 100,        # 刷新阈值
    "large_dataset_threshold": 10000,  # 大数据集阈值
    "insert_buffer_size": 1000,    # 插入缓冲区大小
    "index_params": {
        "small": {                 # 小数据集索引参数
            "index_type": "FLAT",
            "metric_type": "L2",
            "params": {}
        },
        "medium": {                # 中等数据集索引参数
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {
                "nlist": 1024
            }
        },
        "large": {                 # 大数据集索引参数
            "index_type": "IVF_SQ8",
            "metric_type": "L2",
            "params": {
                "nlist": 4096
            }
        }
    }
}

# 嵌入模型配置
EMBEDDING_CONFIG = {
    "model": "text-embedding-nomic-embed-text-v1.5",  # 默认嵌入模型
    "batch_size": 20,             # 批处理大小
    "max_retries": 3,             # 最大重试次数
    "retry_interval": 5,          # 重试间隔（秒）
    "timeout": 30                 # 超时时间（秒）
}

# 文档处理配置
DOCUMENT_PROCESSOR_CONFIG = {
    "min_content_length": 10,      # 最小内容长度
    "max_content_length": 100000,  # 最大内容长度
    "cache_enabled": True,         # 是否启用缓存
    "cache_dir": "data/cache"      # 缓存目录
}

# 文档分割配置
SPLITTER_CONFIG = {
    "paragraph": {
        "min_length": 100,
        "max_length": 1000,
        "overlap": 50,
        "cache_dir": str(CACHE_DIR)      # 缓存目录
    },
    "qa": {
        "min_length": 50,
        "max_length": 500,
        "overlap": 20,
        "cache_dir": str(SPLITTER_CACHE_DIR)  # 缓存目录
    }
}

# 缓存配置
CACHE_CONFIG = {
    "enabled": True,              # 是否启用缓存
    "expiry": 3600,              # 缓存过期时间（秒）
    "key_prefix": "rag:",        # 缓存键前缀
    "max_size": 1000             # 最大缓存条目数
}

# 字段定义
class Field:
    """字段名称常量"""
    ID = "id"
    VECTOR = "vector"
    PAGE_CONTENT = "page_content"
    METADATA = "metadata"
    GROUP_ID = "group_id"
    SPARSE_VECTOR = "sparse_vector"

# 距离度量类型
class Distance:
    """距离度量类型常量"""
    L2 = "L2"
    IP = "IP"
    COSINE = "COSINE"

# 索引类型
class IndexType:
    """索引类型常量"""
    FLAT = "FLAT"
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    HNSW = "HNSW"
    TEXT = "TEXT"

class Field(Enum):
    CONTENT_KEY = "page_content"      # 文本内容
    METADATA_KEY = "metadata"         # 元数据
    GROUP_KEY = "group_id"           # 分组ID
    VECTOR = "vector"                # 向量
    SPARSE_VECTOR = "sparse_vector"  # 稀疏向量（用于全文搜索）
    TEXT_KEY = "text"               # 文本
    PRIMARY_KEY = "id"              # 主键
    DOC_ID = "metadata.doc_id"      # 文档ID
    DOCUMENT_ID = "metadata.document_id"  # 文档ID

class IndexType:
    HNSW = "hnsw"
    TEXT = "text"
    PAYLOAD = "payload"

class Distance:
    COSINE = "cosine"
    EUCLID = "euclid"
    DOT = "dot" 