import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status
from app.api.v1.endpoints.llm import get_discover_models, register_from_discovery

@pytest.mark.asyncio
@patch("app.services.llm_service.llm_service.discover_local_models")
async def test_get_discover_models_forwards_correctly(mock_service):
    """测试llm模块中discover_models路由的转发功能"""
    # 模拟返回的模型列表
    mock_models = [
        {"id": "model1", "name": "Model 1"},
        {"id": "model2", "name": "Model 2"}
    ]
    
    # 设置模拟服务的返回值
    mock_service.return_value = mock_models
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    
    # 调用测试函数
    result = await get_discover_models(
        provider="test_provider", 
        url="http://test.url", 
        current_user=mock_user
    )
    
    # 验证结果和服务调用
    assert result == mock_models
    mock_service.assert_called_once_with("test_provider", "http://test.url")

@pytest.mark.asyncio
@patch("app.services.llm_service.llm_service.create_llm")
async def test_register_from_discovery_forwards_correctly(mock_create_service):
    """测试llm模块中register_from_discovery路由的转发功能"""
    # 模拟返回的模型
    mock_model = MagicMock()
    mock_model.id = "test_model_id"
    mock_model.name = "Test Model"
    
    # 设置模拟服务的返回值
    mock_create_service.return_value = mock_model
    
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
        current_user=mock_user
    )
    
    # 验证结果
    assert result == mock_model
    
    # 验证服务被调用
    mock_create_service.assert_called_once()
    # 验证调用参数
    call_args = mock_create_service.call_args[0][0]
    assert call_args.name == "Test Model"
    assert call_args.provider == "test_provider"
    assert call_args.model_type == "test_model_id"
    assert call_args.api_url == "http://test.url"
    assert call_args.description == "Test Description"
    assert call_args.context_window == 4096
    assert call_args.default is True 