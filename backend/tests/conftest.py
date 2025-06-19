"""
pytest配置文件

提供全局的测试配置、fixtures和工具函数。
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import patch
from pathlib import Path
from typing import Dict, Any, Generator

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入MongoDB模拟模块
from tests.mocks.mongodb_mock import mongodb as mock_mongodb

# 导入测试工具
from tests.utils.test_helpers import TestDataManager, APITestHelper, TempFileHelper
from tests.utils.data_generators import user_generator, doc_generator, config_generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建事件循环

    Yields:
        asyncio.AbstractEventLoop: 事件循环
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_mongo():
    """提供模拟MongoDB实例并替换真实的MongoDB连接"""
    with patch('app.db.mongodb.mongodb', mock_mongodb):
        yield mock_mongodb


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """
    测试用户数据

    Returns:
        Dict: 用户数据字典
    """
    return user_generator.generate_user_data()


@pytest.fixture
def test_auth_token() -> str:
    """
    测试认证令牌

    Returns:
        str: JWT令牌
    """
    return user_generator.generate_auth_token()


@pytest.fixture
def api_client(test_auth_token: str) -> APITestHelper:
    """
    API客户端

    Args:
        test_auth_token: 认证令牌

    Returns:
        APITestHelper: API测试辅助类实例
    """
    return APITestHelper(
        base_url="http://localhost:8000",
        auth_token=test_auth_token
    )


@pytest.fixture
def temp_file_helper() -> Generator[TempFileHelper, None, None]:
    """
    临时文件辅助器

    Yields:
        TempFileHelper: 临时文件辅助类实例
    """
    helper = TempFileHelper()
    yield helper
    helper.cleanup()


@pytest.fixture
def test_data_manager() -> TestDataManager:
    """
    测试数据管理器

    Returns:
        TestDataManager: 测试数据管理器实例
    """
    return TestDataManager()


@pytest.fixture
def sample_document_content() -> str:
    """
    示例文档内容

    Returns:
        str: 文档内容
    """
    return doc_generator.generate_simple_text()


@pytest.fixture
def sample_split_config() -> Dict[str, Any]:
    """
    示例分割配置

    Returns:
        Dict: 分割配置
    """
    return config_generator.generate_split_config()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    设置测试环境

    自动执行的session级别fixture，用于设置测试环境。
    """
    # 设置测试环境变量
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # 确保测试目录存在
    test_dirs = [
        "fixtures/documents",
        "fixtures/responses",
        "fixtures/configs",
        "unit",
        "integration",
        "utils"
    ]

    for test_dir in test_dirs:
        dir_path = Path(__file__).parent / test_dir
        dir_path.mkdir(parents=True, exist_ok=True)

    yield

    # 清理测试环境
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


# 测试标记定义
def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "unit: 标记单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试"
    )
    config.addinivalue_line(
        "markers", "api: 标记API测试"
    )
    config.addinivalue_line(
        "markers", "document: 标记文档相关测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 根据文件路径自动添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # 根据测试名称添加标记
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)
        if "document" in item.name.lower():
            item.add_marker(pytest.mark.document)
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)