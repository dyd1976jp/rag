"""
RAG模块的异常定义

这个模块定义了RAG系统中可能出现的各种异常类型，以便更精确地捕获和处理错误。
"""

class RAGBaseException(Exception):
    """RAG系统异常的基类"""
    pass

# 文档处理相关异常
class DocumentProcessError(RAGBaseException):
    """文档处理过程中的基本异常"""
    pass

class DocumentValidationError(DocumentProcessError):
    """文档验证失败"""
    pass

class DocumentCleaningError(DocumentProcessError):
    """文档清洗过程中的错误"""
    pass

class DocumentSplitError(DocumentProcessError):
    """文档分割过程中的错误"""
    pass

class FileProcessError(DocumentProcessError):
    """文件处理过程中的错误"""
    pass

class PDFProcessError(FileProcessError):
    """PDF处理特定错误"""
    pass

# 向量存储相关异常
class VectorStoreError(RAGBaseException):
    """向量存储相关异常"""
    pass

class CollectionCreateError(VectorStoreError):
    """创建集合失败"""
    pass

class CollectionLoadError(VectorStoreError):
    """加载集合失败"""
    pass

class IndexCreateError(VectorStoreError):
    """创建索引失败"""
    pass

class SearchError(VectorStoreError):
    """搜索过程中的错误"""
    pass

class InsertError(VectorStoreError):
    """插入数据失败"""
    pass

class DeleteError(VectorStoreError):
    """删除数据失败"""
    pass

class QueryError(VectorStoreError):
    """查询失败"""
    pass

# 嵌入模型相关异常
class EmbeddingError(RAGBaseException):
    """嵌入模型相关异常"""
    pass

class ModelConnectionError(EmbeddingError):
    """连接嵌入模型服务失败"""
    pass

class EmbeddingTimeoutError(EmbeddingError):
    """嵌入生成超时"""
    pass

class EmbeddingBatchError(EmbeddingError):
    """批量嵌入失败"""
    pass

# 检索服务相关异常
class RetrievalError(RAGBaseException):
    """检索服务异常"""
    pass

class RerankingError(RetrievalError):
    """重排序异常"""
    pass

# 缓存相关异常
class CacheError(RAGBaseException):
    """缓存服务异常"""
    pass

class RedisConnectionError(CacheError):
    """Redis连接失败"""
    pass 