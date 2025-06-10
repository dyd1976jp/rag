"""
测试配置文件
"""
import pytest
import sys
import os
import asyncio
from unittest.mock import patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入MongoDB模拟模块
from tests.mocks.mongodb_mock import mongodb as mock_mongodb


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_mongo():
    """提供模拟MongoDB实例并替换真实的MongoDB连接"""
    with patch('app.db.mongodb.mongodb', mock_mongodb):
        yield mock_mongodb 