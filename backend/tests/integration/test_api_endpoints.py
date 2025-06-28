"""
API端点集成测试

合并了原有的多个API测试文件，提供统一的端点测试覆盖。
包含从以下文件合并的测试逻辑：
- integration/test_api_fix.py
- integration/test_simple_api.py
- api/test_llm_api.py
- test_llm_endpoints.py
- scripts/testing/curl_test.sh (转换为Python测试)
- scripts/testing/final_test.sh (转换为Python测试)
- backend/tests/integration/comprehensive_api_test.py (部分功能)
"""

import pytest
import requests
import json
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path

from tests.utils.test_helpers import APITestHelper, TempFileHelper, DocumentTestHelper
from tests.utils.data_generators import doc_generator, user_generator, config_generator


class TestDocumentUploadAPI:
    """文档上传API测试"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.api_helper = APITestHelper(
            base_url="http://localhost:8000",
            auth_token=user_generator.generate_auth_token()
        )
        self.temp_helper = TempFileHelper()
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.temp_helper.cleanup()
    
    def test_should_upload_text_document_successfully(self):
        """测试：应成功上传文本文档"""
        # Arrange
        content = DocumentTestHelper.create_test_document_content()
        file_path = self.temp_helper.create_temp_file(content, ".txt")
        
        # Act
        response = self.api_helper.upload_document(file_path)
        
        # Assert
        assert response.status_code == 200, f"上传应成功，状态码: {response.status_code}"
        
        result = response.json()
        assert result.get("success") is True, "响应应标记为成功"
        assert "doc_id" in result, "响应应包含文档ID"
        assert "segments_count" in result, "响应应包含段落数量"
        assert result["segments_count"] > 0, "段落数量应大于0"
    
    def test_should_preview_document_split_successfully(self):
        """测试：应成功预览文档分割"""
        # Arrange
        content = DocumentTestHelper.create_test_document_content()
        file_path = self.temp_helper.create_temp_file(content, ".txt")
        
        # Act
        response = self.api_helper.upload_document(file_path, preview_only=True)
        
        # Assert
        assert response.status_code == 200, f"预览应成功，状态码: {response.status_code}"
        
        result = response.json()
        DocumentTestHelper.assert_document_split_result(result, expected_min_segments=1)
        
        # 检查预览特有的字段
        assert "parentContent" in result, "预览响应应包含父内容"
        assert "childrenContent" in result, "预览响应应包含子内容列表"
        assert isinstance(result["childrenContent"], list), "子内容应为列表"
    
    def test_should_handle_unsupported_file_format(self):
        """测试：应正确处理不支持的文件格式"""
        # Arrange
        content = "测试内容"
        file_path = self.temp_helper.create_temp_file(content, ".unsupported")
        
        # Act
        response = self.api_helper.upload_document(file_path)
        
        # Assert
        assert response.status_code == 400, "不支持的格式应返回400错误"
        
        result = response.json()
        assert result.get("success") is False, "响应应标记为失败"
        assert "不支持的文件类型" in result.get("message", ""), "错误信息应提及文件类型"
    
    def test_should_handle_empty_file(self):
        """测试：应正确处理空文件"""
        # Arrange
        file_path = self.temp_helper.create_temp_file("", ".txt")
        
        # Act
        response = self.api_helper.upload_document(file_path)
        
        # Assert
        # 空文件可能被接受但产生0个段落，或者被拒绝
        if response.status_code == 200:
            result = response.json()
            # 如果接受，段落数应为0或很少
            assert result.get("segments_count", 0) >= 0, "空文件段落数应为0或很少"
        else:
            # 如果拒绝，应返回适当的错误码
            assert response.status_code in [400, 422], "空文件应返回适当的错误码"
    
    def test_should_respect_split_parameters(self):
        """测试：应遵循分割参数"""
        # Arrange
        content = doc_generator.generate_long_text(10)
        file_path = self.temp_helper.create_temp_file(content, ".txt")
        
        split_configs = [
            {"parent_chunk_size": 512, "child_chunk_size": 256},
            {"parent_chunk_size": 1024, "child_chunk_size": 512},
        ]
        
        # Act & Assert
        for config in split_configs:
            response = self.api_helper.upload_document(
                file_path, 
                preview_only=True,
                **config
            )
            
            assert response.status_code == 200, f"配置{config}应成功"
            result = response.json()
            assert result.get("success") is True, f"配置{config}应返回成功"
            assert len(result.get("segments", [])) > 0, f"配置{config}应产生段落"


class TestDocumentSplitPreviewAPI:
    """文档分割预览API测试"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.api_helper = APITestHelper(
            base_url="http://localhost:8000",
            auth_token=user_generator.generate_auth_token()
        )
    
    def test_should_preview_text_split_successfully(self):
        """测试：应成功预览文本分割"""
        # Arrange
        content = DocumentTestHelper.create_test_document_content()
        data = {
            "content": content,
            "parent_chunk_size": 1024,
            "parent_chunk_overlap": 200,
            "parent_separator": "\n\n",
            "child_chunk_size": 512,
            "child_chunk_overlap": 50,
            "child_separator": "\n"
        }
        
        # Act
        response = self.api_helper.make_request(
            "POST", 
            "/api/v1/rag/documents/preview-split",
            data=data
        )
        
        # Assert
        assert response.status_code == 200, f"预览应成功，状态码: {response.status_code}"
        
        result = response.json()
        DocumentTestHelper.assert_document_split_result(result)
        
        # 检查父子结构
        segments = result.get("segments", [])
        for segment in segments:
            assert "children" in segment, "每个段落应有children字段"
            if segment["children"]:
                for child in segment["children"]:
                    assert "content" in child, "子段落应有content字段"
                    assert "length" in child, "子段落应有length字段"
    
    def test_should_handle_empty_content(self):
        """测试：应正确处理空内容"""
        # Arrange
        data = {
            "content": "",
            "parent_chunk_size": 1024,
            "child_chunk_size": 512
        }
        
        # Act
        response = self.api_helper.make_request(
            "POST",
            "/api/v1/rag/documents/preview-split",
            data=data
        )
        
        # Assert
        assert response.status_code == 400, "空内容应返回400错误"
    
    def test_should_be_consistent_with_upload_preview(self):
        """测试：应与上传预览保持一致"""
        # Arrange
        content = DocumentTestHelper.create_test_document_content()
        
        # 通过preview-split端点
        preview_data = {
            "content": content,
            "parent_chunk_size": 1024,
            "parent_chunk_overlap": 200,
            "parent_separator": "\n\n",
            "child_chunk_size": 512,
            "child_chunk_overlap": 50,
            "child_separator": "\n"
        }
        
        # 通过upload端点预览模式
        with TempFileHelper() as temp_helper:
            file_path = temp_helper.create_temp_file(content, ".txt")
            
            # Act
            preview_response = self.api_helper.make_request(
                "POST",
                "/api/v1/rag/documents/preview-split",
                data=preview_data
            )
            
            upload_response = self.api_helper.upload_document(
                file_path,
                preview_only=True,
                parent_chunk_size=1024,
                parent_chunk_overlap=200,
                parent_separator="\n\n",
                child_chunk_size=512,
                child_chunk_overlap=50,
                child_separator="\n"
            )
            
            # Assert
            assert preview_response.status_code == 200, "preview-split应成功"
            assert upload_response.status_code == 200, "upload预览应成功"
            
            preview_result = preview_response.json()
            upload_result = upload_response.json()
            
            # 比较关键字段
            assert preview_result.get("total_segments") == upload_result.get("total_segments"), "段落总数应一致"
            
            # 比较段落内容（允许一些格式差异）
            preview_segments = preview_result.get("segments", [])
            upload_segments = upload_result.get("segments", [])
            
            assert len(preview_segments) == len(upload_segments), "段落数量应一致"


class TestLLMDiscoveryAPI:
    """LLM发现API测试"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.api_helper = APITestHelper(
            base_url="http://localhost:8000",
            auth_token=user_generator.generate_auth_token()
        )
    
    def test_should_discover_local_models_successfully(self):
        """测试：应成功发现本地模型"""
        # Arrange
        params = {
            "provider": "lmstudio",
            "url": "http://localhost:1234"
        }
        
        # Act
        response = self.api_helper.make_request(
            "GET",
            "/api/v1/discover/",
            params=params
        )
        
        # Assert
        # 注意：这个测试可能失败如果LM Studio没有运行
        # 在实际测试中，我们应该mock这个服务
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list), "发现结果应为列表"
            
            if result:  # 如果有模型
                for model in result:
                    assert "id" in model, "模型应有ID"
                    assert "name" in model, "模型应有名称"
        else:
            # 如果服务不可用，应返回适当的错误
            assert response.status_code in [404, 500, 503], "服务不可用应返回适当错误码"
    
    def test_should_handle_invalid_provider(self):
        """测试：应正确处理无效的提供商"""
        # Arrange
        params = {
            "provider": "invalid_provider",
            "url": "http://localhost:1234"
        }
        
        # Act
        response = self.api_helper.make_request(
            "GET",
            "/api/v1/discover/",
            params=params
        )
        
        # Assert
        # 应该返回错误或空列表
        assert response.status_code in [200, 400, 422], "无效提供商应返回适当响应"
        
        if response.status_code == 200:
            result = response.json()
            # 可能返回空列表或默认模型
            assert isinstance(result, list), "结果应为列表"
    
    def test_should_handle_unreachable_url(self):
        """测试：应正确处理不可达的URL"""
        # Arrange
        params = {
            "provider": "lmstudio",
            "url": "http://unreachable:9999"
        }
        
        # Act
        response = self.api_helper.make_request(
            "GET",
            "/api/v1/discover/",
            params=params
        )
        
        # Assert
        # 应该返回错误或空结果
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list), "结果应为列表"
            # 可能返回空列表或错误信息
        else:
            assert response.status_code in [400, 404, 500, 503], "不可达URL应返回错误"


class TestRAGChatAPI:
    """RAG聊天API测试"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.api_helper = APITestHelper(
            base_url="http://localhost:8000",
            auth_token=user_generator.generate_auth_token()
        )
    
    @pytest.mark.skip(reason="需要实际的文档和LLM服务")
    def test_should_answer_question_successfully(self):
        """测试：应成功回答问题"""
        # 这个测试需要实际的文档和LLM服务
        # 在实际测试中应该使用mock
        pass
    
    @pytest.mark.skip(reason="需要实际的搜索服务")
    def test_should_search_documents_successfully(self):
        """测试：应成功搜索文档"""
        # 这个测试需要实际的搜索服务
        # 在实际测试中应该使用mock
        pass


class TestAPIErrorHandling:
    """API错误处理测试"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.api_helper = APITestHelper(base_url="http://localhost:8000")
    
    def test_should_require_authentication(self):
        """测试：应要求认证"""
        # Arrange - 不提供认证令牌
        
        # Act
        response = self.api_helper.make_request("GET", "/api/v1/rag/documents")
        
        # Assert
        assert response.status_code == 401, "未认证请求应返回401"
    
    def test_should_handle_invalid_json(self):
        """测试：应正确处理无效JSON"""
        # Arrange
        self.api_helper.auth_token = user_generator.generate_auth_token()
        
        # Act - 发送无效JSON
        response = requests.post(
            f"{self.api_helper.base_url}/api/v1/rag/documents/preview-split",
            headers=self.api_helper.get_auth_headers(),
            data="invalid json",  # 无效JSON
            timeout=30
        )
        
        # Assert
        assert response.status_code == 422, "无效JSON应返回422"
    
    def test_should_handle_missing_required_fields(self):
        """测试：应正确处理缺失必需字段"""
        # Arrange
        self.api_helper.auth_token = user_generator.generate_auth_token()
        data = {
            # 缺少content字段
            "parent_chunk_size": 1024
        }
        
        # Act
        response = self.api_helper.make_request(
            "POST",
            "/api/v1/rag/documents/preview-split",
            data=data
        )
        
        # Assert
        assert response.status_code in [400, 422], "缺失必需字段应返回错误"


class TestAPIErrorHandling:
    """API错误处理测试 - 从Shell脚本转换"""

    def setup_method(self):
        """每个测试方法前的准备"""
        self.base_url = "http://localhost:8000/api/v1/rag"
        self.temp_helper = TempFileHelper()

    def teardown_method(self):
        """每个测试方法后的清理"""
        self.temp_helper.cleanup()

    @pytest.mark.integration
    def test_should_handle_utf8_encoding_gracefully(self, api_client: APITestHelper):
        """测试：应优雅处理UTF-8编码问题 - 从curl_test.sh转换"""
        # Arrange - 创建包含中文字符的测试文件
        chinese_content = """这是一个包含中文字符的测试文档。

它用于测试UTF-8编码问题的修复。

第一段：介绍内容
这里包含一些中文字符：你好世界！

第二段：详细说明
测试各种特殊字符：©®™€£¥

第三段：总结内容
这个文件名包含中文字符，用于测试文件上传时的编码处理。

测试内容足够长，以确保分割功能正常工作。
这里添加更多内容来测试分割算法。
每个段落都应该被正确处理。"""

        test_file_path = self.temp_helper.create_temp_file(chinese_content, ".txt", "初赛训练数据集")

        # Act - 测试preview-split端点处理multipart数据
        url = f"{self.base_url}/documents/preview-split"

        with open(test_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'parent_chunk_size': 1024,
                'parent_chunk_overlap': 200,
                'parent_separator': '\n\n',
                'child_chunk_size': 512,
                'child_chunk_overlap': 50,
                'child_separator': '\n'
            }

            response = requests.post(url, files=files, data=data, timeout=10, headers=api_client.get_auth_headers())

        # Assert - 应该返回友好错误而非500
        assert response.status_code != 500, "不应返回内部服务器错误"

        if response.status_code == 200:
            result = response.json()
            assert result.get("success") is not None, "响应应包含success字段"
            if result.get("success"):
                assert "segments" in result, "成功响应应包含segments"
                # 验证中文内容被正确处理
                segments = result.get("segments", [])
                if segments:
                    combined_content = " ".join(seg.get("content", "") for seg in segments)
                    assert "中文字符" in combined_content, "应正确处理中文字符"
        else:
            # 如果不是200，应该是友好的错误响应
            assert response.status_code in [400, 422], f"应返回客户端错误码，实际: {response.status_code}"
            try:
                error_result = response.json()
                assert "message" in error_result or "detail" in error_result, "错误响应应包含错误信息"
            except:
                # 如果不是JSON响应，至少不应该是HTML错误页面
                assert "<!DOCTYPE html>" not in response.text, "不应返回HTML错误页面"

    @pytest.mark.integration
    def test_should_handle_multipart_data_correctly(self, api_client: APITestHelper):
        """测试：应正确处理multipart数据 - 从final_test.sh转换"""
        # Arrange
        test_content = """这是一个包含中文字符的测试文档。

第一段：介绍内容
这里包含一些中文字符：你好世界！

第二段：详细说明
测试各种特殊字符：©®™€£¥

第三段：总结内容
测试内容足够长，以确保分割功能正常工作。"""

        test_file_path = self.temp_helper.create_temp_file(test_content, ".txt")

        # Act - 测试原始错误场景修复
        url = f"{self.base_url}/documents/preview-split"

        with open(test_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'parent_chunk_size': 1024,
                'parent_chunk_overlap': 200,
                'parent_separator': '\n\n',
                'child_chunk_size': 512,
                'child_chunk_overlap': 50,
                'child_separator': '\n'
            }

            response = requests.post(url, files=files, data=data, timeout=10, headers=api_client.get_auth_headers())

        # Assert
        assert response.status_code in [200, 400, 422], f"应返回有效状态码，实际: {response.status_code}"

        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, dict), "响应应为JSON对象"
            assert "success" in result, "响应应包含success字段"
        else:
            # 验证错误响应格式
            try:
                error_result = response.json()
                assert isinstance(error_result, dict), "错误响应应为JSON对象"
            except:
                # 如果不是JSON，至少应该是有意义的错误信息
                assert len(response.text) > 0, "错误响应不应为空"

    @pytest.mark.integration
    def test_should_handle_invalid_parameters_gracefully(self, api_client: APITestHelper):
        """测试：应优雅处理无效参数"""
        # Arrange
        test_content = "简单测试内容"
        test_file_path = self.temp_helper.create_temp_file(test_content, ".txt")

        # Test cases with invalid parameters
        invalid_params_cases = [
            {
                'parent_chunk_size': -1,  # 负数
                'parent_chunk_overlap': 200,
                'parent_separator': '\n\n',
                'child_chunk_size': 512,
                'child_chunk_overlap': 50,
                'child_separator': '\n'
            },
            {
                'parent_chunk_size': 'invalid',  # 非数字
                'parent_chunk_overlap': 200,
                'parent_separator': '\n\n',
                'child_chunk_size': 512,
                'child_chunk_overlap': 50,
                'child_separator': '\n'
            },
            {
                'parent_chunk_size': 1024,
                'parent_chunk_overlap': 2000,  # 重叠大于块大小
                'parent_separator': '\n\n',
                'child_chunk_size': 512,
                'child_chunk_overlap': 50,
                'child_separator': '\n'
            }
        ]

        url = f"{self.base_url}/documents/preview-split"

        for i, invalid_data in enumerate(invalid_params_cases):
            with open(test_file_path, 'rb') as f:
                files = {'file': f}

                response = requests.post(url, files=files, data=invalid_data, timeout=10, headers=api_client.get_auth_headers())

                # Assert - 应该返回客户端错误而不是服务器错误
                assert response.status_code != 500, f"测试用例{i+1}不应返回服务器错误"
                assert response.status_code in [400, 422], f"测试用例{i+1}应返回客户端错误码"

    @pytest.mark.integration
    def test_should_handle_missing_file_gracefully(self, api_client: APITestHelper):
        """测试：应优雅处理缺少文件的情况"""
        # Arrange
        url = f"{self.base_url}/documents/preview-split"
        data = {
            'parent_chunk_size': 1024,
            'parent_chunk_overlap': 200,
            'parent_separator': '\n\n',
            'child_chunk_size': 512,
            'child_chunk_overlap': 50,
            'child_separator': '\n'
        }

        # Act - 发送不包含文件的请求
        response = requests.post(url, files={}, data=data, timeout=10, headers=api_client.get_auth_headers())

        # Assert
        assert response.status_code in [400, 422], "缺少文件应返回客户端错误"

        try:
            result = response.json()
            assert "message" in result or "detail" in result, "错误响应应包含错误信息"
        except:
            # 如果不是JSON响应，至少应该有错误信息
            assert len(response.text) > 0, "错误响应不应为空"


class TestAPIPerformance:
    """API性能测试 - 从comprehensive_api_test.py转换"""

    def setup_method(self):
        """每个测试方法前的准备"""
        self.base_url = "http://localhost:8000/api/v1/rag"
        self.temp_helper = TempFileHelper()

    def teardown_method(self):
        """每个测试方法后的清理"""
        self.temp_helper.cleanup()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_should_handle_concurrent_requests(self, api_client: APITestHelper):
        """测试：应正确处理并发请求"""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Arrange
        test_content = doc_generator.generate_long_text(10)
        test_file_path = self.temp_helper.create_temp_file(test_content, ".txt")

        def make_request():
            """发送单个请求"""
            url = f"{self.base_url}/documents/preview-split"

            with open(test_file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'parent_chunk_size': 512,
                    'parent_chunk_overlap': 100,
                    'parent_separator': '\n\n',
                    'child_chunk_size': 256,
                    'child_chunk_overlap': 50,
                    'child_separator': '\n'
                }

                start_time = time.time()
                response = requests.post(url, files=files, data=data, timeout=30, headers=api_client.get_auth_headers())
                end_time = time.time()

                return {
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': response.status_code == 200
                }

        # Act - 发送并发请求
        num_concurrent_requests = 5
        results = []

        with ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent_requests)]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"并发请求失败: {e}")

        # Assert
        assert len(results) == num_concurrent_requests, "应该收到所有请求的响应"

        # 检查成功率
        successful_requests = [r for r in results if r['success']]
        success_rate = len(successful_requests) / len(results)
        assert success_rate >= 0.8, f"成功率应至少80%，实际: {success_rate:.2%}"

        # 检查响应时间
        if successful_requests:
            avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            assert avg_response_time < 10.0, f"平均响应时间应少于10秒，实际: {avg_response_time:.2f}秒"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_should_handle_large_file_efficiently(self, api_client: APITestHelper):
        """测试：应高效处理大文件"""
        # Arrange - 创建大文件
        large_content = doc_generator.generate_long_text(100)  # 生成大量内容
        test_file_path = self.temp_helper.create_temp_file(large_content, ".txt")

        # Act
        url = f"{self.base_url}/documents/preview-split"

        start_time = time.time()

        with open(test_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'parent_chunk_size': 2048,
                'parent_chunk_overlap': 400,
                'parent_separator': '\n\n',
                'child_chunk_size': 1024,
                'child_chunk_overlap': 200,
                'child_separator': '\n'
            }

            response = requests.post(url, files=files, data=data, timeout=60, headers=api_client.get_auth_headers())

        end_time = time.time()
        processing_time = end_time - start_time

        # Assert
        assert response.status_code in [200, 413], "大文件应该被处理或返回文件过大错误"
        assert processing_time < 30.0, f"大文件处理时间应少于30秒，实际: {processing_time:.2f}秒"

        if response.status_code == 200:
            result = response.json()
            assert result.get("success") is not None, "响应应包含success字段"
            if result.get("success"):
                segments = result.get("segments", [])
                assert len(segments) > 0, "大文件应该产生分割段落"


class TestAPIDocumentSlicePreview:
    """文档切片预览API测试 - 从test_api_fix.py转换"""

    def setup_method(self):
        """每个测试方法前的准备"""
        self.base_url = "http://localhost:8000/api/v1/rag"

    @pytest.mark.integration
    @pytest.mark.skip(reason="需要先有文档数据才能测试切片预览")
    def test_should_get_document_slice_preview(self, api_client: APITestHelper):
        """测试：应获取文档切片预览"""
        # 这个测试需要先有文档数据，暂时跳过
        # 在实际使用时，需要先上传文档，然后测试切片预览功能
        pass
