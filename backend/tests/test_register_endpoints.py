import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status
from app.services.llm_service import LLMService

@pytest.mark.asyncio
@patch("app.services.llm_service.llm_service.register_discovered_model")
async def test_discover_register_model(mock_register):
    """测试discover模块的register_model函数"""
    # 导入测试对象 - 放在这里避免循环导入
    from app.api.v1.endpoints.discover import register_model
    
    # 模拟返回的模型
    mock_model = AsyncMock()
    mock_model.id = "test_model_id"
    mock_model.name = "Test Model"
    
    # 设置模拟函数的返回值
    mock_register.return_value = mock_model
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    mock_user.is_superuser = True
    
    # 调用测试函数
    result = await register_model(
        llm_model_id="test_model_id",
        provider="test_provider",
        name="Test Model",
        api_url="http://test.url",
        description="Test Description",
        context_window=4096,
        set_as_default=True,
        max_output_tokens=2000,
        temperature=0.8,
        custom_options={"key": "value"},
        current_user=mock_user
    )
    
    # 验证结果
    assert result == mock_model
    
    # 验证服务被调用
    mock_register.assert_called_once()
    # 验证调用参数
    call_args = mock_register.call_args[1]
    assert call_args["model_id"] == "test_model_id"
    assert call_args["provider"] == "test_provider"
    assert call_args["name"] == "Test Model"
    assert call_args["api_url"] == "http://test.url"
    assert call_args["description"] == "Test Description"
    assert call_args["context_window"] == 4096
    assert call_args["set_as_default"] is True
    assert call_args["max_output_tokens"] == 2000
    assert call_args["temperature"] == 0.8
    assert call_args["custom_options"] == {"key": "value"}

@pytest.mark.asyncio
@patch("app.services.llm_service.llm_service.register_discovered_model")
async def test_llm_register_from_discovery(mock_register):
    """测试llm模块的register_from_discovery函数"""
    # 导入测试对象
    from app.api.v1.endpoints.llm import register_from_discovery
    
    # 模拟返回的模型
    mock_model = AsyncMock()
    mock_model.id = "test_model_id"
    mock_model.name = "Test Model"
    
    # 设置模拟函数的返回值
    mock_register.return_value = mock_model
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    mock_user.is_superuser = True
    
    # 调用测试函数
    result = await register_from_discovery(
        llm_model_id="test_model_id",
        provider="test_provider",
        name="Test Model",
        api_url="http://test.url",
        description="Test Description",
        context_window=4096,
        set_as_default=True,
        max_output_tokens=2000,
        temperature=0.8,
        custom_options={"key": "value"},
        current_user=mock_user
    )
    
    # 验证结果
    assert result == mock_model
    
    # 验证服务被调用
    mock_register.assert_called_once()
    # 验证调用参数
    call_args = mock_register.call_args[1]
    assert call_args["model_id"] == "test_model_id"
    assert call_args["provider"] == "test_provider"
    assert call_args["name"] == "Test Model"
    assert call_args["api_url"] == "http://test.url"
    assert call_args["description"] == "Test Description"
    assert call_args["context_window"] == 4096
    assert call_args["set_as_default"] is True
    assert call_args["max_output_tokens"] == 2000
    assert call_args["temperature"] == 0.8
    assert call_args["custom_options"] == {"key": "value"}

@pytest.mark.asyncio
@patch("app.services.llm_service.LLMService.create_llm")
async def test_register_discovered_model_service(mock_create_llm):
    """测试LLMService的register_discovered_model方法"""
    # 模拟创建结果
    mock_model = MagicMock()
    mock_model.id = "test_id"
    mock_model.name = "Test Model"
    mock_model.provider = "test_provider"
    mock_model.model_type = "test_model_id"
    mock_model.api_url = "http://test.url"
    mock_create_llm.return_value = mock_model
    
    # 创建服务实例
    service = LLMService()
    
    # 调用测试方法
    result = await service.register_discovered_model(
        model_id="test_model_id",
        provider="test_provider",
        name="Test Model",
        api_url="http://test.url",
        description="Test Description",
        context_window=4096,
        set_as_default=True,
        max_output_tokens=2000,
        temperature=0.8,
        custom_options={"key": "value"}
    )
    
    # 验证结果
    assert result == mock_model
    
    # 验证方法调用
    mock_create_llm.assert_called_once()
    
    # 验证创建参数
    call_args = mock_create_llm.call_args[0][0]
    assert call_args.name == "Test Model"
    assert call_args.provider == "test_provider"
    assert call_args.model_type == "test_model_id"
    assert call_args.api_url == "http://test.url"
    assert call_args.description == "Test Description"
    assert call_args.context_window == 4096
    assert call_args.default is True
    assert call_args.max_output_tokens == 2000
    assert call_args.temperature == 0.8
    assert "key" in call_args.config
    assert call_args.config["key"] == "value"

@pytest.mark.asyncio
async def test_register_model_permission_denied():
    """测试注册模型时的权限检查"""
    # 导入测试对象
    from app.api.v1.endpoints.discover import register_model
    
    # 模拟非管理员用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    mock_user.is_superuser = False
    
    # 验证抛出权限错误
    with pytest.raises(HTTPException) as exc_info:
        await register_model(
            llm_model_id="test_model_id",
            provider="test_provider",
            name="Test Model",
            api_url="http://test.url",
            current_user=mock_user
        )
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "权限不足" in exc_info.value.detail

@pytest.mark.asyncio
async def test_register_from_discovery_permission_denied():
    """测试register_from_discovery端点的权限检查"""
    # 导入测试对象
    from app.api.v1.endpoints.llm import register_from_discovery
    
    # 模拟非管理员用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    mock_user.is_superuser = False
    
    # 验证抛出权限错误
    with pytest.raises(HTTPException) as exc_info:
        await register_from_discovery(
            llm_model_id="test_model_id",
            provider="test_provider",
            name="Test Model",
            api_url="http://test.url",
            current_user=mock_user
        )
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "权限不足" in exc_info.value.detail 