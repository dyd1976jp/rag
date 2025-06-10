import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, status
from app.api.v1.endpoints.discover import discover_models, register_model

@pytest.mark.asyncio
async def test_discover_models_returns_empty_list_when_no_models():
    """测试当没有发现模型时返回空列表"""
    # 创建模拟服务和请求
    mock_service = AsyncMock()
    mock_service.return_value = []
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    
    with patch("app.services.llm_service.llm_service.discover_local_models", mock_service):
        result = await discover_models(provider="test_provider", url="http://test.url", current_user=mock_user)
    
    assert result == []
    mock_service.assert_called_once_with("test_provider", "http://test.url")

@pytest.mark.asyncio
async def test_discover_models_returns_models_list():
    """测试正常返回模型列表"""
    # 模拟返回的模型列表
    mock_models = [
        {"id": "model1", "name": "Model 1"},
        {"id": "model2", "name": "Model 2"}
    ]
    
    # 创建模拟服务和请求
    mock_service = AsyncMock()
    mock_service.return_value = mock_models
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    
    with patch("app.services.llm_service.llm_service.discover_local_models", mock_service):
        result = await discover_models(provider="test_provider", url="http://test.url", current_user=mock_user)
    
    assert result == mock_models
    mock_service.assert_called_once_with("test_provider", "http://test.url")

@pytest.mark.asyncio
async def test_discover_models_corrects_url():
    """测试自动修正URL格式"""
    # 创建模拟服务和请求
    mock_service = AsyncMock()
    mock_service.return_value = []
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    
    with patch("app.services.llm_service.llm_service.discover_local_models", mock_service):
        await discover_models(provider="test_provider", url="localhost:1234", current_user=mock_user)
    
    # 验证调用时URL已被修正
    mock_service.assert_called_once_with("test_provider", "http://localhost:1234")

@pytest.mark.asyncio
async def test_discover_models_raises_exception_on_error():
    """测试当服务返回错误时抛出异常"""
    # 创建模拟服务和请求
    mock_service = AsyncMock()
    mock_service.return_value = [{"error": "测试错误"}]
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    
    with pytest.raises(HTTPException) as exc_info:
        with patch("app.services.llm_service.llm_service.discover_local_models", mock_service):
            await discover_models(provider="test_provider", url="http://test.url", current_user=mock_user)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "测试错误"

@pytest.mark.asyncio
async def test_discover_models_catches_general_exceptions():
    """测试捕获一般异常并返回错误信息"""
    # 创建模拟服务和请求
    mock_service = AsyncMock()
    mock_service.side_effect = Exception("一般错误")
    
    # 模拟当前用户
    mock_user = AsyncMock()
    mock_user.id = "test_user_id"
    
    with patch("app.services.llm_service.llm_service.discover_local_models", mock_service):
        result = await discover_models(provider="test_provider", url="http://test.url", current_user=mock_user)
    
    assert len(result) == 1
    assert "error" in result[0]
    assert "一般错误" in result[0]["error"] 