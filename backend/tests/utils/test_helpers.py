"""
测试辅助函数模块

提供通用的测试工具函数，用于简化测试代码编写。
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient


class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self, fixtures_dir: str = "fixtures"):
        """
        初始化测试数据管理器
        
        Args:
            fixtures_dir: 测试数据目录
        """
        self.fixtures_dir = Path(__file__).parent.parent / fixtures_dir
        self.fixtures_dir.mkdir(exist_ok=True)
    
    def load_json_fixture(self, filename: str) -> Dict[str, Any]:
        """
        加载JSON测试数据
        
        Args:
            filename: 文件名
            
        Returns:
            Dict: JSON数据
        """
        file_path = self.fixtures_dir / "responses" / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_json_fixture(self, filename: str, data: Dict[str, Any]) -> None:
        """
        保存JSON测试数据
        
        Args:
            filename: 文件名
            data: 要保存的数据
        """
        file_path = self.fixtures_dir / "responses" / filename
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_test_document(self, content: str, filename: str = "test.txt") -> str:
        """
        创建测试文档
        
        Args:
            content: 文档内容
            filename: 文件名
            
        Returns:
            str: 文件路径
        """
        file_path = self.fixtures_dir / "documents" / filename
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(file_path)


class APITestHelper:
    """API测试辅助类"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: Optional[str] = None):
        """
        初始化API测试辅助类
        
        Args:
            base_url: API基础URL
            auth_token: 认证令牌
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = requests.Session()
        
        if auth_token:
            self.session.headers.update({
                "Authorization": f"Bearer {auth_token}"
            })
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证头
        
        Returns:
            Dict: 认证头字典
        """
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    def make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> requests.Response:
        """
        发送API请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            files: 文件数据
            params: 查询参数
            
        Returns:
            requests.Response: 响应对象
        """
        url = f"{self.base_url}{endpoint}"
        
        kwargs = {
            "headers": self.get_auth_headers(),
            "timeout": 30
        }
        
        if data:
            kwargs["json"] = data
        if files:
            kwargs["files"] = files
        if params:
            kwargs["params"] = params
        
        return self.session.request(method, url, **kwargs)
    
    def upload_document(
        self, 
        file_path: str, 
        preview_only: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        上传文档
        
        Args:
            file_path: 文件路径
            preview_only: 是否仅预览
            **kwargs: 其他参数
            
        Returns:
            requests.Response: 响应对象
        """
        with open(file_path, 'rb') as f:
            files = {"file": f}
            data = {"preview_only": preview_only, **kwargs}
            return self.make_request("POST", "/api/v1/rag/documents/upload", files=files, data=data)


class MockServiceHelper:
    """模拟服务辅助类"""
    
    @staticmethod
    def mock_mongodb_response(data: List[Dict[str, Any]]) -> Mock:
        """
        模拟MongoDB响应
        
        Args:
            data: 模拟数据
            
        Returns:
            Mock: 模拟对象
        """
        mock_cursor = Mock()
        mock_cursor.to_list.return_value = data
        return mock_cursor
    
    @staticmethod
    def mock_milvus_response(vectors: List[List[float]], distances: List[float]) -> Mock:
        """
        模拟Milvus响应
        
        Args:
            vectors: 向量列表
            distances: 距离列表
            
        Returns:
            Mock: 模拟对象
        """
        mock_result = Mock()
        mock_result.ids = list(range(len(vectors)))
        mock_result.distances = distances
        return mock_result
    
    @staticmethod
    def mock_openai_response(content: str) -> Mock:
        """
        模拟OpenAI响应
        
        Args:
            content: 响应内容
            
        Returns:
            Mock: 模拟对象
        """
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = content
        return mock_response


class DocumentTestHelper:
    """文档测试辅助类"""
    
    @staticmethod
    def create_test_document_content() -> str:
        """
        创建测试文档内容
        
        Returns:
            str: 测试文档内容
        """
        return """第一章：引言

这是第一章的内容。
它包含多行文本。
用于测试文档分割功能。

第二章：方法

这是第二章的内容。
包含了详细的方法描述。
这里有更多的技术细节。

第三章：结果

实验结果如下：
1. 结果一：性能提升显著
2. 结果二：准确率达到95%
3. 结果三：用户满意度高

第四章：总结

总结内容在这里。
这是项目的最终结论。"""
    
    @staticmethod
    def create_test_pdf_content() -> bytes:
        """
        创建测试PDF内容（模拟）
        
        Returns:
            bytes: PDF字节内容
        """
        # 这里返回一个简单的PDF头部，实际测试中可能需要真实的PDF文件
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    
    @staticmethod
    def assert_document_split_result(result: Dict[str, Any], expected_min_segments: int = 1) -> None:
        """
        断言文档分割结果
        
        Args:
            result: 分割结果
            expected_min_segments: 期望的最小段落数
        """
        assert result.get("success") is True, "分割应该成功"
        assert "segments" in result, "结果应包含segments字段"
        assert len(result["segments"]) >= expected_min_segments, f"段落数应至少为{expected_min_segments}"
        
        for i, segment in enumerate(result["segments"]):
            assert "content" in segment, f"段落{i}应包含content字段"
            assert "length" in segment, f"段落{i}应包含length字段"
            assert len(segment["content"]) > 0, f"段落{i}内容不应为空"


class TempFileHelper:
    """临时文件辅助类"""
    
    def __init__(self):
        """初始化临时文件辅助类"""
        self.temp_files: List[str] = []
        self.temp_dirs: List[str] = []
    
    def create_temp_file(self, content: str, suffix: str = ".txt") -> str:
        """
        创建临时文件
        
        Args:
            content: 文件内容
            suffix: 文件后缀
            
        Returns:
            str: 临时文件路径
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        self.temp_files.append(temp_path)
        return temp_path
    
    def create_temp_dir(self) -> str:
        """
        创建临时目录
        
        Returns:
            str: 临时目录路径
        """
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def cleanup(self) -> None:
        """清理临时文件和目录"""
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except (OSError, FileNotFoundError):
                pass
        
        for dir_path in self.temp_dirs:
            try:
                shutil.rmtree(dir_path)
            except (OSError, FileNotFoundError):
                pass
        
        self.temp_files.clear()
        self.temp_dirs.clear()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


# 全局测试辅助实例
test_data_manager = TestDataManager()
api_helper = APITestHelper()
mock_helper = MockServiceHelper()
doc_helper = DocumentTestHelper()
