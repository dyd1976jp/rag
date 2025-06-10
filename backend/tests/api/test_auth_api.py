import pytest
from httpx import AsyncClient
import asyncio
from datetime import datetime
from app.main import app
from unittest.mock import patch
from tests.mocks.mongodb_mock import mongodb as mock_mongodb

# 测试用户数据
test_user_data = {
    "email": f"test_api_user_{datetime.now().timestamp()}@test.com",
    "username": f"test_api_user_{datetime.now().timestamp()}",
    "password": "Test@Password123"
}

@pytest.mark.asyncio
async def test_register_and_login(mock_mongo, monkeypatch):
    """测试用户注册和登录API"""
    # 使用MockClient模拟FastAPI客户端
    app.dependency_overrides = {}  # 清除可能的依赖覆盖
    
    # 替换应用中的MongoDB实例
    with patch('app.db.mongodb.mongodb', mock_mongo), \
         patch('app.services.user.mongodb', mock_mongo):
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 确保测试前数据库已连接
            await mock_mongo.connect_to_database()
            
            try:
                # 测试注册API
                print(f"测试注册API，用户: {test_user_data['email']}")
                response = await client.post(
                    "/api/v1/auth/register",
                    json=test_user_data
                )
                assert response.status_code == 200
                register_data = response.json()
                assert register_data["email"] == test_user_data["email"]
                assert register_data["username"] == test_user_data["username"]
                print(f"注册成功，用户ID: {register_data['id']}")
                
                # 测试登录API - 通过邮箱
                print(f"测试邮箱登录API")
                response = await client.post(
                    "/api/v1/auth/login",
                    data={
                        "username": test_user_data["email"],
                        "password": test_user_data["password"]
                    }
                )
                assert response.status_code == 200
                login_data = response.json()
                assert "access_token" in login_data
                assert login_data["token_type"] == "bearer"
                print(f"邮箱登录成功")
                
                # 测试登录API - 通过用户名
                print(f"测试用户名登录API")
                response = await client.post(
                    "/api/v1/auth/login",
                    data={
                        "username": test_user_data["username"],
                        "password": test_user_data["password"]
                    }
                )
                assert response.status_code == 200
                login_data = response.json()
                assert "access_token" in login_data
                print(f"用户名登录成功")
                
                # 测试错误密码
                print(f"测试错误密码登录")
                response = await client.post(
                    "/api/v1/auth/login",
                    data={
                        "username": test_user_data["email"],
                        "password": "WrongPassword"
                    }
                )
                assert response.status_code == 401
                print(f"错误密码登录失败，符合预期")
                
            finally:
                # 清理测试数据
                print(f"清理测试用户: {test_user_data['email']}")
                await mock_mongo.db.users.delete_one({"email": test_user_data["email"]})
                await mock_mongo.close_database_connection()

if __name__ == "__main__":
    # 直接运行此文件进行测试
    pytest.main(["-xvs", __file__]) 