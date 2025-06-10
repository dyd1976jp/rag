import pytest
import os
import sys
import numpy as np
from unittest.mock import patch, MagicMock, call
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.rag.retrieval_service import RetrievalService
from app.rag.document_processor import Document
from app.rag.custom_exceptions import (
    RetrievalError, VectorStoreError, EmbeddingError, 
    RerankingError, CacheError
)

class TestRetrievalService:
    """检索服务测试类"""

    @pytest.fixture
    def mock_vector_store(self):
        """模拟向量存储"""
        mock = MagicMock()
        mock.collection = MagicMock()
        return mock

    @pytest.fixture
    def mock_embedding_model(self):
        """模拟嵌入模型"""
        mock = MagicMock()
        # 模拟嵌入向量生成
        mock.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]
        mock.get_dimension.return_value = 4
        return mock

    @pytest.fixture
    def mock_cache_service(self):
        """模拟缓存服务"""
        mock = MagicMock()
        mock.enabled = True
        mock.get_cached_results.return_value = None  # 默认缓存未命中
        return mock

    @pytest.fixture
    def retrieval_service(self, mock_vector_store, mock_embedding_model, mock_cache_service):
        """创建检索服务实例"""
        config = {
            "top_k": 3,
            "score_threshold": 0.5,
            "score_threshold_enabled": True,
            "max_retries": 2,
            "retry_interval": 1,
            "reranking_model": {
                "enabled": False,
                "model": "default"
            }
        }
        return RetrievalService(
            vector_store=mock_vector_store,
            embedding_model=mock_embedding_model,
            retrieval_config=config,
            cache_service=mock_cache_service
        )

    @pytest.fixture
    def sample_documents(self):
        """创建测试文档"""
        return [
            Document(
                page_content="这是测试文档1的内容",
                metadata={"doc_id": "doc1", "parent_id": "parent1", "score": 0.9}
            ),
            Document(
                page_content="这是测试文档2的内容",
                metadata={"doc_id": "doc2", "parent_id": "parent2", "score": 0.8}
            ),
            Document(
                page_content="这是测试文档3的内容",
                metadata={"doc_id": "doc3", "parent_id": "parent3", "score": 0.7}
            )
        ]

    def test_retrieve_with_cache_hit(self, retrieval_service, mock_cache_service, sample_documents):
        """测试缓存命中时的检索"""
        # 设置缓存命中
        mock_cache_service.get_cached_results.return_value = sample_documents
        
        # 执行测试
        results = retrieval_service.retrieve(
            query="测试查询",
            dataset_id="test_dataset",
            use_cache=True
        )
        
        # 验证结果
        mock_cache_service.get_cached_results.assert_called_once_with("测试查询", "test_dataset")
        assert results == sample_documents
        # 验证没有调用向量存储和嵌入模型
        retrieval_service.vector_store.search_by_vector.assert_not_called()
        retrieval_service.embedding_model.embed_query.assert_not_called()

    def test_retrieve_without_cache(self, retrieval_service, mock_embedding_model, mock_vector_store, sample_documents):
        """测试不使用缓存的检索"""
        # 设置模拟返回值
        mock_vector_store.search_by_vector.return_value = sample_documents
        
        # 执行测试
        results = retrieval_service.retrieve(
            query="测试查询",
            dataset_id="test_dataset",
            use_cache=False
        )
        
        # 验证结果
        assert results == sample_documents
        mock_embedding_model.embed_query.assert_called_once_with("测试查询")
        mock_vector_store.search_by_vector.assert_called_once()

    def test_retrieve_with_reranking(self, retrieval_service, mock_embedding_model, mock_vector_store, sample_documents):
        """测试带重排序的检索"""
        # 启用重排序
        retrieval_service.retrieval_config["reranking_model"]["enabled"] = True
        
        # 设置模拟返回值
        mock_vector_store.search_by_vector.return_value = sample_documents
        
        # 为文档内容嵌入设置不同的返回值
        mock_embedding_model.embed_query.side_effect = [
            [0.1, 0.2, 0.3, 0.4],  # 查询向量
            [0.2, 0.3, 0.4, 0.5],  # 文档1向量
            [0.3, 0.4, 0.5, 0.6],  # 文档2向量
            [0.4, 0.5, 0.6, 0.7]   # 文档3向量
        ]
        
        # 执行测试
        results = retrieval_service.retrieve(
            query="测试查询",
            dataset_id="test_dataset",
            use_cache=False
        )
        
        # 验证结果
        assert len(results) == 3
        # 验证嵌入模型调用
        assert mock_embedding_model.embed_query.call_count == 4
        # 验证重排序后的分数已更新
        assert all("score" in doc.metadata for doc in results)
        
        # 恢复设置
        retrieval_service.retrieval_config["reranking_model"]["enabled"] = False

    def test_retrieve_with_parent(self, retrieval_service, mock_vector_store, sample_documents):
        """测试带父文档的检索"""
        # 设置模拟返回值
        mock_vector_store.search_by_vector.return_value = sample_documents
        
        # 设置父文档的模拟返回值
        parent_docs = [
            Document(
                page_content=f"这是父文档{i+1}的内容",
                metadata={"doc_id": f"parent{i+1}"}
            )
            for i in range(3)
        ]
        
        # 配置get_by_id方法根据不同ID返回不同父文档
        def mock_get_by_id(doc_id):
            for i, parent_id in enumerate(["parent1", "parent2", "parent3"]):
                if doc_id == parent_id:
                    return parent_docs[i]
            return None
            
        mock_vector_store.get_by_id.side_effect = mock_get_by_id
        
        # 执行测试
        results = retrieval_service.retrieve_with_parent(
            query="测试查询",
            dataset_id="test_dataset"
        )
        
        # 验证结果
        assert len(results) == 3
        # 验证每个结果都包含子文档和父文档
        for i, result in enumerate(results):
            assert result["child_document"] == sample_documents[i]
            assert result["parent_document"] == parent_docs[i]
            assert result["score"] == sample_documents[i].metadata["score"]
        
        # 验证get_by_id调用
        expected_calls = [call("parent1"), call("parent2"), call("parent3")]
        mock_vector_store.get_by_id.assert_has_calls(expected_calls)

    def test_retrieve_with_missing_parent(self, retrieval_service, mock_vector_store, sample_documents):
        """测试父文档缺失的情况"""
        # 设置模拟返回值
        mock_vector_store.search_by_vector.return_value = sample_documents
        
        # 设置get_by_id返回None，模拟父文档缺失
        mock_vector_store.get_by_id.return_value = None
        
        # 执行测试
        results = retrieval_service.retrieve_with_parent(
            query="测试查询",
            dataset_id="test_dataset"
        )
        
        # 验证结果
        assert len(results) == 3
        # 验证每个结果都包含子文档但父文档为None
        for i, result in enumerate(results):
            assert result["child_document"] == sample_documents[i]
            assert result["parent_document"] is None
            assert result["score"] == sample_documents[i].metadata["score"]

    def test_rerank_results(self, retrieval_service, mock_embedding_model, sample_documents):
        """测试重排序功能"""
        # 设置嵌入向量的模拟返回值
        mock_embedding_model.embed_query.side_effect = [
            [0.1, 0.2, 0.3, 0.4],  # 查询向量
            [0.9, 0.8, 0.7, 0.6],  # 文档1向量 - 相似度较低
            [0.2, 0.3, 0.4, 0.5],  # 文档2向量 - 相似度较高
            [0.5, 0.5, 0.5, 0.5]   # 文档3向量 - 相似度中等
        ]
        
        # 执行测试
        reranked = retrieval_service._rerank_results("测试查询", sample_documents)
        
        # 验证结果
        assert len(reranked) == 3
        # 验证重排序后的顺序（根据相似度）
        # 文档2应该排第一（相似度最高）
        assert reranked[0].metadata["doc_id"] == "doc2"
        # 文档3应该排第二
        assert reranked[1].metadata["doc_id"] == "doc3"
        # 文档1应该排第三（相似度最低）
        assert reranked[2].metadata["doc_id"] == "doc1"
        
        # 验证分数已更新
        assert all("score" in doc.metadata for doc in reranked)

    def test_retry_operation(self, retrieval_service):
        """测试重试操作"""
        # 创建一个会失败两次然后成功的模拟函数
        mock_func = MagicMock()
        mock_func.side_effect = [
            EmbeddingError("第一次失败"),
            EmbeddingError("第二次失败"),
            "成功结果"
        ]
        
        # 执行测试
        result = retrieval_service._retry_operation(
            mock_func,
            "测试参数",
            error_type=EmbeddingError,
            kwarg1="值1"
        )
        
        # 验证结果
        assert result == "成功结果"
        assert mock_func.call_count == 3
        # 验证调用参数
        mock_func.assert_called_with("测试参数", kwarg1="值1")

    def test_retry_operation_max_retries(self, retrieval_service):
        """测试达到最大重试次数"""
        # 创建一个总是失败的模拟函数
        mock_func = MagicMock()
        mock_func.side_effect = EmbeddingError("总是失败")
        
        # 执行测试并验证异常
        with pytest.raises(EmbeddingError, match="总是失败"):
            retrieval_service._retry_operation(
                mock_func,
                "测试参数",
                error_type=EmbeddingError
            )
        
        # 验证调用次数（初始调用 + 最大重试次数）
        assert mock_func.call_count == retrieval_service.max_retries

    def test_error_handling_in_retrieve(self, retrieval_service, mock_embedding_model):
        """测试检索过程中的错误处理"""
        # 设置嵌入模型抛出异常
        mock_embedding_model.embed_query.side_effect = EmbeddingError("嵌入生成失败")
        
        # 执行测试并验证异常
        with pytest.raises(RetrievalError, match="生成查询向量失败"):
            retrieval_service.retrieve("测试查询")
        
        # 验证调用次数（考虑重试）
        assert mock_embedding_model.embed_query.call_count == retrieval_service.max_retries
        
    def test_retrieve_with_score_threshold(self, retrieval_service, mock_vector_store):
        """测试带分数阈值的检索"""
        # 创建不同分数的测试文档
        test_docs = [
            Document(page_content="高分文档", metadata={"score": 0.9}),
            Document(page_content="中分文档", metadata={"score": 0.6}),
            Document(page_content="低分文档", metadata={"score": 0.3})
        ]
        
        # 设置模拟返回值
        mock_vector_store.search_by_vector.return_value = test_docs
        
        # 执行测试，设置分数阈值为0.5
        results = retrieval_service.retrieve(
            query="测试查询",
            score_threshold=0.5,
            use_cache=False
        )
        
        # 验证结果 - 只有高分和中分文档应该被返回
        assert len(results) == 2
        assert results[0].page_content == "高分文档"
        assert results[1].page_content == "中分文档"
        
    def test_integration_retrieval_cache_reranking(self, retrieval_service, mock_vector_store, mock_embedding_model, mock_cache_service, sample_documents):
        """测试检索、缓存和重排序的集成"""
        # 1. 设置缓存未命中
        mock_cache_service.get_cached_results.return_value = None
        
        # 2. 设置向量存储返回结果
        mock_vector_store.search_by_vector.return_value = sample_documents
        
        # 3. 启用重排序
        retrieval_service.retrieval_config["reranking_model"]["enabled"] = True
        
        # 4. 设置嵌入向量
        mock_embedding_model.embed_query.side_effect = [
            [0.1, 0.2, 0.3, 0.4],  # 查询向量
            [0.9, 0.8, 0.7, 0.6],  # 文档1向量
            [0.2, 0.3, 0.4, 0.5],  # 文档2向量
            [0.5, 0.5, 0.5, 0.5]   # 文档3向量
        ]
        
        # 5. 执行第一次检索
        results = retrieval_service.retrieve(
            query="测试查询",
            dataset_id="test_dataset",
            use_cache=True
        )
        
        # 验证结果
        assert len(results) == 3
        # 验证嵌入模型和向量存储被调用
        mock_embedding_model.embed_query.assert_called()
        mock_vector_store.search_by_vector.assert_called_once()
        # 验证结果已缓存
        mock_cache_service.cache_results.assert_called_once()
        
        # 6. 重置模拟对象
        mock_embedding_model.reset_mock()
        mock_vector_store.reset_mock()
        mock_cache_service.reset_mock()
        
        # 7. 设置缓存命中
        mock_cache_service.get_cached_results.return_value = results
        
        # 8. 执行第二次检索
        cached_results = retrieval_service.retrieve(
            query="测试查询",
            dataset_id="test_dataset",
            use_cache=True
        )
        
        # 验证结果
        assert cached_results == results
        # 验证嵌入模型和向量存储没有被调用
        mock_embedding_model.embed_query.assert_not_called()
        mock_vector_store.search_by_vector.assert_not_called()
        # 验证从缓存获取结果
        mock_cache_service.get_cached_results.assert_called_once()
        
        # 恢复设置
        retrieval_service.retrieval_config["reranking_model"]["enabled"] = False 