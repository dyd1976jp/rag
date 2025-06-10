import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.rag.cache_service import CacheService
from app.rag.document_processor import Document
from app.rag.custom_exceptions import CacheError, RedisConnectionError

class TestCacheService:
    """缓存服务测试类"""

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            # 设置ping方法返回True，表示连接成功
            mock_instance.ping.return_value = True
            yield mock_instance

    @pytest.fixture
    def cache_service(self, mock_redis_client):
        """创建缓存服务实例"""
        with patch("redis.Redis", return_value=mock_redis_client):
            config = {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "key_prefix": "test_cache:",
                "expiry": 3600
            }
            yield CacheService(config)

    @pytest.fixture
    def sample_documents(self):
        """创建测试文档"""
        return [
            Document(
                page_content="这是测试文档1的内容",
                metadata={"doc_id": "doc1", "source": "test"}
            ),
            Document(
                page_content="这是测试文档2的内容",
                metadata={"doc_id": "doc2", "source": "test"}
            )
        ]

    def test_init_success(self, mock_redis_client):
        """测试成功初始化缓存服务"""
        with patch("redis.Redis", return_value=mock_redis_client):
            cache_service = CacheService({
                "host": "localhost",
                "port": 6379,
                "db": 0
            })
            
            assert cache_service.enabled is True
            assert cache_service.redis_client == mock_redis_client
            mock_redis_client.ping.assert_called_once()

    def test_init_failure(self):
        """测试初始化失败时禁用缓存"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            # 设置ping方法抛出异常
            mock_instance.ping.side_effect = Exception("连接失败")
            
            cache_service = CacheService({
                "host": "invalid_host",
                "port": 6379,
                "db": 0
            })
            
            assert cache_service.enabled is False

    def test_get_cached_results_hit(self, cache_service, mock_redis_client, sample_documents):
        """测试获取缓存命中"""
        # 准备测试数据
        query = "测试查询"
        dataset_id = "test_dataset"
        cache_key = f"{cache_service.key_prefix}retrieval:{dataset_id}:{query}"
        
        # 模拟缓存数据
        cached_data = json.dumps([
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in sample_documents
        ])
        
        # 设置模拟返回值
        mock_redis_client.get.return_value = cached_data
        
        # 执行测试
        results = cache_service.get_cached_results(query, dataset_id)
        
        # 验证结果
        mock_redis_client.get.assert_called_once_with(cache_key)
        assert len(results) == 3
        assert results[0].page_content == sample_documents[0].page_content
        assert results[1].metadata["doc_id"] == sample_documents[1].metadata["doc_id"]

    def test_get_cached_results_miss(self, cache_service, mock_redis_client):
        """测试缓存未命中"""
        # 准备测试数据
        query = "未缓存查询"
        dataset_id = "test_dataset"
        
        # 设置模拟返回值为None（缓存未命中）
        mock_redis_client.get.return_value = None
        
        # 执行测试
        results = cache_service.get_cached_results(query, dataset_id)
        
        # 验证结果
        assert results is None

    def test_get_cached_results_disabled(self):
        """测试禁用缓存时获取缓存结果"""
        # 创建禁用的缓存服务
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.side_effect = Exception("连接失败")
            
            cache_service = CacheService()
            assert cache_service.enabled is False
            
            # 执行测试
            results = cache_service.get_cached_results("查询", "dataset")
            
            # 验证结果
            assert results is None
            # 确保没有调用Redis方法
            mock_instance.get.assert_not_called()

    def test_cache_results(self, cache_service, mock_redis_client, sample_documents):
        """测试缓存结果"""
        # 准备测试数据
        query = "测试查询"
        dataset_id = "test_dataset"
        cache_key = f"{cache_service.key_prefix}retrieval:{dataset_id}:{query}"
        
        # 执行测试
        cache_service.cache_results(query, dataset_id, sample_documents)
        
        # 验证结果
        mock_redis_client.setex.assert_called_once()
        # 验证调用参数
        args, kwargs = mock_redis_client.setex.call_args
        assert args[0] == cache_key
        assert args[1] == cache_service.expiry
        # 验证JSON数据包含正确的文档内容
        cached_data = json.loads(args[2])
        assert len(cached_data) == 3
        assert cached_data[0]["page_content"] == sample_documents[0].page_content
        assert cached_data[1]["metadata"]["doc_id"] == sample_documents[1].metadata["doc_id"]

    def test_invalidate_cache(self, cache_service, mock_redis_client):
        """测试使缓存失效"""
        # 准备测试数据
        dataset_id = "test_dataset"
        pattern = f"{cache_service.key_prefix}retrieval:{dataset_id}:*"
        mock_keys = ["key1", "key2", "key3"]
        
        # 设置模拟返回值
        mock_redis_client.keys.return_value = mock_keys
        
        # 执行测试
        cache_service.invalidate_cache(dataset_id)
        
        # 验证结果
        mock_redis_client.keys.assert_called_once_with(pattern)
        mock_redis_client.delete.assert_called_once_with(*mock_keys)

    def test_clear_all_cache(self, cache_service, mock_redis_client):
        """测试清除所有缓存"""
        # 准备测试数据
        pattern = f"{cache_service.key_prefix}*"
        mock_keys = ["key1", "key2", "key3", "key4"]
        
        # 设置模拟返回值
        mock_redis_client.keys.return_value = mock_keys
        
        # 执行测试
        cache_service.clear_all_cache()
        
        # 验证结果
        mock_redis_client.keys.assert_called_once_with(pattern)
        mock_redis_client.delete.assert_called_once_with(*mock_keys)

    def test_error_handling(self, cache_service, mock_redis_client):
        """测试错误处理"""
        # 设置模拟方法抛出异常
        mock_redis_client.get.side_effect = Exception("Redis错误")
        
        # 执行测试并验证不会抛出异常
        result = cache_service.get_cached_results("查询", "dataset")
        assert result is None
        
    def test_cache_empty_results(self, cache_service, mock_redis_client):
        """测试缓存空结果"""
        # 准备测试数据
        query = "空结果查询"
        dataset_id = "test_dataset"
        
        # 执行测试
        cache_service.cache_results(query, dataset_id, [])
        
        # 验证结果 - 不应该调用setex
        mock_redis_client.setex.assert_not_called()
        
    def test_cache_with_custom_expiry(self):
        """测试自定义过期时间"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            # 创建带自定义过期时间的缓存服务
            config = {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "key_prefix": "test_cache:",
                "expiry": 7200  # 自定义过期时间：2小时
            }
            cache_service = CacheService(config)
            
            # 验证过期时间已正确设置
            assert cache_service.expiry == 7200
            
            # 测试缓存操作
            doc = Document(page_content="测试", metadata={"id": "test"})
            cache_service.cache_results("查询", "dataset", [doc])
            
            # 验证调用参数
            args, kwargs = mock_instance.setex.call_args
            assert args[1] == 7200  # 验证使用了自定义过期时间 