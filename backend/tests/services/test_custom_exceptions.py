import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.rag.custom_exceptions import (
    RAGBaseException,
    DocumentProcessError, DocumentValidationError, DocumentCleaningError, DocumentSplitError,
    FileProcessError, PDFProcessError,
    VectorStoreError, CollectionCreateError, CollectionLoadError, IndexCreateError,
    SearchError, InsertError, DeleteError, QueryError,
    EmbeddingError, ModelConnectionError, EmbeddingTimeoutError, EmbeddingBatchError,
    RetrievalError, RerankingError,
    CacheError, RedisConnectionError
)

class TestCustomExceptions:
    """异常处理系统测试类"""

    def test_exception_hierarchy(self):
        """测试异常继承层次结构"""
        # 测试基础异常
        assert issubclass(RAGBaseException, Exception)
        
        # 测试一级异常
        assert issubclass(DocumentProcessError, RAGBaseException)
        assert issubclass(VectorStoreError, RAGBaseException)
        assert issubclass(EmbeddingError, RAGBaseException)
        assert issubclass(RetrievalError, RAGBaseException)
        assert issubclass(CacheError, RAGBaseException)
        
        # 测试二级异常
        assert issubclass(DocumentValidationError, DocumentProcessError)
        assert issubclass(DocumentCleaningError, DocumentProcessError)
        assert issubclass(DocumentSplitError, DocumentProcessError)
        assert issubclass(FileProcessError, DocumentProcessError)
        
        assert issubclass(CollectionCreateError, VectorStoreError)
        assert issubclass(CollectionLoadError, VectorStoreError)
        assert issubclass(IndexCreateError, VectorStoreError)
        assert issubclass(SearchError, VectorStoreError)
        assert issubclass(InsertError, VectorStoreError)
        assert issubclass(DeleteError, VectorStoreError)
        assert issubclass(QueryError, VectorStoreError)
        
        assert issubclass(ModelConnectionError, EmbeddingError)
        assert issubclass(EmbeddingTimeoutError, EmbeddingError)
        assert issubclass(EmbeddingBatchError, EmbeddingError)
        
        assert issubclass(RerankingError, RetrievalError)
        
        assert issubclass(RedisConnectionError, CacheError)
        
        # 测试三级异常
        assert issubclass(PDFProcessError, FileProcessError)

    def test_exception_instantiation(self):
        """测试异常实例化"""
        # 测试基础异常
        base_ex = RAGBaseException("基础异常")
        assert str(base_ex) == "基础异常"
        
        # 测试一级异常
        doc_ex = DocumentProcessError("文档处理错误")
        assert str(doc_ex) == "文档处理错误"
        assert isinstance(doc_ex, RAGBaseException)
        
        # 测试二级异常
        validation_ex = DocumentValidationError("验证错误")
        assert str(validation_ex) == "验证错误"
        assert isinstance(validation_ex, DocumentProcessError)
        assert isinstance(validation_ex, RAGBaseException)
        
        # 测试三级异常
        pdf_ex = PDFProcessError("PDF处理错误")
        assert str(pdf_ex) == "PDF处理错误"
        assert isinstance(pdf_ex, FileProcessError)
        assert isinstance(pdf_ex, DocumentProcessError)
        assert isinstance(pdf_ex, RAGBaseException)

    def test_exception_catching(self):
        """测试异常捕获"""
        # 测试捕获特定异常
        try:
            raise DocumentValidationError("文档验证失败")
        except DocumentValidationError as e:
            assert str(e) == "文档验证失败"
        
        # 测试捕获父类异常
        try:
            raise DocumentValidationError("文档验证失败")
        except DocumentProcessError as e:
            assert str(e) == "文档验证失败"
        
        # 测试捕获基类异常
        try:
            raise CollectionCreateError("创建集合失败")
        except RAGBaseException as e:
            assert str(e) == "创建集合失败"
            assert isinstance(e, VectorStoreError)

    def test_exception_with_context(self):
        """测试带上下文的异常"""
        # 测试异常链
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as e:
                raise EmbeddingError("嵌入错误") from e
        except EmbeddingError as e:
            assert str(e) == "嵌入错误"
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "原始错误"

    def test_custom_attributes(self):
        """测试异常自定义属性"""
        # 创建带自定义属性的异常
        class CustomSearchError(SearchError):
            def __init__(self, message, query=None, results=None):
                super().__init__(message)
                self.query = query
                self.results = results
        
        # 测试自定义属性
        ex = CustomSearchError("搜索失败", query="测试查询", results=[])
        assert str(ex) == "搜索失败"
        assert ex.query == "测试查询"
        assert ex.results == [] 