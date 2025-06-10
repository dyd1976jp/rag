import pytest
from httpx import AsyncClient
import asyncio
from datetime import datetime
from app.main import app
from unittest.mock import patch, MagicMock
from tests.mocks.mongodb_mock import mongodb as mock_mongodb

# 测试LLM数据
test_llm_data = {
    "name": f"test_api_llm_{datetime.now().timestamp()}",
    "provider": "Test Provider",
    "model_type": "Test Model",
    "api_url": "http://localhost:8000/test",
    "api_key": "test_api_key"
}

@pytest.mark.asyncio
async def test_llm_api_no_auth(mock_mongo, monkeypatch):
    """测试LLM API（无需认证的部分）"""
    # 使用MockClient模拟FastAPI客户端
    app.dependency_overrides = {}  # 清除可能的依赖覆盖
    
    # 模拟数据库访问
    with patch('app.db.mongodb.mongodb', mock_mongo), \
         patch('app.services.llm_service.mongodb', mock_mongo):
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 确保测试前数据库已连接
            await mock_mongo.connect_to_database()
            
            try:
                # 先在数据库中创建一个模型
                llm_dict = test_llm_data.copy()
                llm_dict["created_at"] = datetime.now()
                llm_dict["updated_at"] = datetime.now()
                llm_dict["status"] = "active"
                llm_dict["default"] = True
                
                # 直接插入测试LLM到数据库
                result = await mock_mongo.db.llms.insert_one(llm_dict)
                llm_id = result.inserted_id
                print(f"直接创建测试LLM，ID: {llm_id}")
                
                # 测试获取LLM列表
                list_response = await client.get("/api/v1/llms/")  # 我们移除了认证需求
                assert list_response.status_code == 200
                llms = list_response.json()
                assert isinstance(llms, list)
                assert len(llms) > 0
                print(f"成功获取LLM列表，数量: {len(llms)}")
                
                # 测试获取单个LLM
                get_response = await client.get(f"/api/v1/llms/{llm_id}")
                assert get_response.status_code == 200
                llm = get_response.json()
                assert llm["id"] == str(llm_id)
                print(f"成功获取LLM: {llm['name']}")
                
                # 测试获取默认LLM
                default_response = await client.get("/api/v1/llms/default")
                assert default_response.status_code == 200
                default_llm = default_response.json()
                assert default_llm["id"] == str(llm_id)
                print(f"成功获取默认LLM: {default_llm['name']}")
                
            finally:
                # 清理测试数据
                await mock_mongo.db.llms.delete_many({"name": {"$regex": f"^{test_llm_data['name']}"}})
                await mock_mongo.close_database_connection()

if __name__ == "__main__":
    # 直接运行此文件进行测试
    pytest.main(["-xvs", __file__]) 