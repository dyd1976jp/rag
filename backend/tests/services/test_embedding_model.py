import pytest
import os
import sys
import time
from unittest.mock import patch, MagicMock, call
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.rag.embedding_model import EmbeddingModel
from app.rag.custom_exceptions import EmbeddingError, ModelConnectionError, EmbeddingTimeoutError, EmbeddingBatchError

class TestEmbeddingModel:
    """嵌入模型测试类"""

    @pytest.fixture
    def mock_requests(self):
        """模拟requests库"""
        with patch("requests.post") as mock_post:
            # 创建模拟响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]
            }
            mock_post.return_value = mock_response
            yield mock_post

    @pytest.fixture
    def embedding_model(self):
        """创建嵌入模型实例"""
        model = EmbeddingModel(
            model_name="test-model",
            api_base="http://test-api"
        )
        # 设置较小的批处理大小以便测试
        model.max_batch_size = 10
        return model

    def test_init(self):
        """测试初始化"""
        model = EmbeddingModel(
            model_name="custom-model",
            api_base="http://custom-api"
        )
        assert model.model_name == "custom-model"
        assert model.api_base == "http://custom-api"
        assert model.max_batch_size > 0
        assert model.max_retries > 0

    def test_embed_query(self, embedding_model, mock_requests):
        """测试单个查询嵌入"""
        # 执行测试
        embedding = embedding_model.embed_query("测试查询")
        
        # 验证结果
        assert embedding == [0.1, 0.2, 0.3, 0.4]
        mock_requests.assert_called_once_with(
            "http://test-api/v1/embeddings",
            json={"model": "test-model", "input": "测试查询"},
            timeout=embedding_model.timeout
        )

    def test_embed_query_error(self, embedding_model, mock_requests):
        """测试查询嵌入错误处理"""
        # 设置模拟响应返回错误
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "错误信息"
        mock_requests.return_value = mock_response
        
        # 执行测试并验证异常
        with pytest.raises(EmbeddingError, match="API调用失败"):
            embedding_model.embed_query("测试查询")

    def test_embed_documents_small_batch(self, embedding_model, mock_requests):
        """测试小批量文档嵌入"""
        # 设置模拟响应返回多个嵌入向量
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3, 0.4]},
                {"embedding": [0.2, 0.3, 0.4, 0.5]},
                {"embedding": [0.3, 0.4, 0.5, 0.6]}
            ]
        }
        mock_requests.return_value = mock_response
        
        # 执行测试
        texts = ["文本1", "文本2", "文本3"]
        embeddings = embedding_model.embed_documents(texts)
        
        # 验证结果
        assert len(embeddings) == 3
        assert embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert embeddings[1] == [0.2, 0.3, 0.4, 0.5]
        assert embeddings[2] == [0.3, 0.4, 0.5, 0.6]
        
        # 验证API调用
        mock_requests.assert_called_once_with(
            "http://test-api/v1/embeddings",
            json={"model": "test-model", "input": texts},
            timeout=embedding_model.timeout
        )

    def test_embed_documents_large_batch(self, embedding_model, mock_requests):
        """测试大批量文档嵌入（需要分批）"""
        # 设置模拟响应
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]} for _ in range(10)]
        }
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "data": [{"embedding": [0.5, 0.6, 0.7, 0.8]} for _ in range(5)]
        }
        
        mock_requests.side_effect = [mock_response1, mock_response2]
        
        # 执行测试
        texts = ["文本" + str(i) for i in range(15)]  # 15个文本，超过批量大小10
        embeddings = embedding_model.embed_documents(texts)
        
        # 验证结果
        assert len(embeddings) == 15
        assert all(len(emb) == 4 for emb in embeddings)
        assert embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert embeddings[10] == [0.5, 0.6, 0.7, 0.8]
        
        # 验证API调用次数和参数
        assert mock_requests.call_count == 2
        mock_requests.assert_has_calls([
            call(
                "http://test-api/v1/embeddings",
                json={"model": "test-model", "input": texts[:10]},
                timeout=embedding_model.timeout
            ),
            call(
                "http://test-api/v1/embeddings",
                json={"model": "test-model", "input": texts[10:]},
                timeout=embedding_model.timeout
            )
        ])

    def test_dynamic_batch_size_adjustment(self, embedding_model):
        """测试动态批量大小调整"""
        # 创建不同长度的文本
        short_texts = ["短文本"] * 20  # 短文本
        medium_texts = ["中等长度的文本，大约有30个字符左右"] * 20  # 中等长度文本
        long_texts = ["这是一个非常长的文本，包含了大量的字符。" * 20] * 20  # 长文本
        
        # 测试短文本（应该使用默认批量大小）
        with patch.object(embedding_model, "_embed_batch_with_retry") as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4]] * 10
            embedding_model.embed_documents(short_texts)
            # 验证调用次数（应该是2次，每次10个文本）
            assert mock_embed.call_count == 2
            # 验证每次调用的文本数量
            assert len(mock_embed.call_args_list[0][0][0]) == 10
            assert len(mock_embed.call_args_list[1][0][0]) == 10
        
        # 测试中等长度文本（应该减小批量大小）
        with patch.object(embedding_model, "_embed_batch_with_retry") as mock_embed:
            # 设置动态批量大小为5
            embedding_model._calculate_batch_size = MagicMock(return_value=5)
            mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4]] * 5
            embedding_model.embed_documents(medium_texts)
            # 验证调用次数（应该是4次，每次5个文本）
            assert mock_embed.call_count == 4
            # 验证每次调用的文本数量
            for i in range(4):
                assert len(mock_embed.call_args_list[i][0][0]) == 5
        
        # 测试长文本（应该显著减小批量大小）
        with patch.object(embedding_model, "_embed_batch_with_retry") as mock_embed:
            # 设置动态批量大小为2
            embedding_model._calculate_batch_size = MagicMock(return_value=2)
            mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4]] * 2
            embedding_model.embed_documents(long_texts)
            # 验证调用次数（应该是10次，每次2个文本）
            assert mock_embed.call_count == 10
            # 验证每次调用的文本数量
            for i in range(10):
                assert len(mock_embed.call_args_list[i][0][0]) == 2

    def test_calculate_batch_size(self, embedding_model):
        """测试批量大小计算逻辑"""
        # 短文本
        short_texts = ["短文本"] * 5
        short_batch_size = embedding_model._calculate_batch_size(short_texts)
        assert short_batch_size <= embedding_model.max_batch_size
        
        # 中等长度文本
        medium_texts = ["中等长度的文本，大约有30个字符左右"] * 5
        medium_batch_size = embedding_model._calculate_batch_size(medium_texts)
        assert medium_batch_size <= embedding_model.max_batch_size
        
        # 长文本
        long_texts = ["这是一个非常长的文本，包含了大量的字符。" * 20] * 5
        long_batch_size = embedding_model._calculate_batch_size(long_texts)
        assert long_batch_size <= embedding_model.max_batch_size
        
        # 验证批量大小随文本长度增加而减小
        assert short_batch_size >= medium_batch_size >= long_batch_size

    def test_batch_time_based_adjustment(self, embedding_model):
        """测试基于处理时间的批量大小调整"""
        # 创建一个模拟的_embed_batch_with_retry方法，第一次调用时耗时较长
        with patch.object(embedding_model, "_embed_batch_with_retry") as mock_embed:
            # 设置第一次调用耗时较长
            def side_effect(texts):
                if mock_embed.call_count == 1:
                    time.sleep(0.1)  # 模拟耗时操作
                return [[0.1, 0.2, 0.3, 0.4]] * len(texts)
            
            mock_embed.side_effect = side_effect
            
            # 创建足够多的文本以触发多次批处理
            texts = ["测试文本"] * 25
            
            # 执行测试
            with patch.object(embedding_model, "_adjust_batch_size_based_on_time") as mock_adjust:
                embeddings = embedding_model.embed_documents(texts)
                
                # 验证结果
                assert len(embeddings) == 25
                # 验证调整批量大小的方法被调用
                assert mock_adjust.called

    def test_retry_mechanism(self, embedding_model, mock_requests):
        """测试重试机制"""
        # 设置模拟响应，前两次失败，第三次成功
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "服务器错误"
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]
        }
        
        mock_requests.side_effect = [error_response, error_response, success_response]
        
        # 设置重试参数
        embedding_model.max_retries = 3
        embedding_model.retry_interval = 0.1
        
        # 执行测试
        embedding = embedding_model.embed_query("测试查询")
        
        # 验证结果
        assert embedding == [0.1, 0.2, 0.3, 0.4]
        assert mock_requests.call_count == 3

    def test_max_retries_exceeded(self, embedding_model, mock_requests):
        """测试超过最大重试次数"""
        # 设置模拟响应，总是失败
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "服务器错误"
        
        mock_requests.return_value = error_response
        
        # 设置重试参数
        embedding_model.max_retries = 3
        embedding_model.retry_interval = 0.1
        
        # 执行测试并验证异常
        with pytest.raises(EmbeddingError):
            embedding_model.embed_query("测试查询")
        
        # 验证调用次数
        assert mock_requests.call_count == 3

    def test_get_dimension(self, embedding_model, mock_requests):
        """测试获取向量维度"""
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]
        }
        mock_requests.return_value = mock_response
        
        # 执行测试
        dimension = embedding_model.get_dimension()
        
        # 验证结果
        assert dimension == 4
        mock_requests.assert_called_once()
        
    def test_empty_input_handling(self, embedding_model):
        """测试空输入处理"""
        # 测试空列表
        result = embedding_model.embed_documents([])
        assert result == []
        
        # 测试None输入
        with pytest.raises(ValueError):
            embedding_model.embed_query(None)
            
    def test_custom_timeout(self):
        """测试自定义超时设置"""
        # 创建带自定义超时的模型
        model = EmbeddingModel(
            model_name="test-model",
            api_base="http://test-api",
            timeout=30  # 自定义超时为30秒
        )
        
        # 验证超时设置
        assert model.timeout == 30
        
        # 测试API调用使用了自定义超时
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]
            }
            mock_post.return_value = mock_response
            
            model.embed_query("测试查询")
            
            # 验证调用参数
            mock_post.assert_called_once_with(
                "http://test-api/v1/embeddings",
                json={"model": "test-model", "input": "测试查询"},
                timeout=30
            ) 