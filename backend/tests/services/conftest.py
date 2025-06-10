import pytest
import os
import sys
from unittest.mock import MagicMock

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.rag.document_processor import Document

@pytest.fixture
def sample_documents():
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

@pytest.fixture
def mock_redis_client():
    """模拟Redis客户端"""
    mock = MagicMock()
    mock.ping.return_value = True
    return mock 