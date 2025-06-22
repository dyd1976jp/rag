import pytest
import asyncio
from datetime import datetime
from app.db.mongodb import mongodb
from unittest.mock import patch
from app.services.user import user_service, UserService
from app.models.user import UserCreate, User

@pytest.mark.asyncio
async def test_user_create(mock_mongo):
    """测试用户创建功能"""
    await mock_mongo.connect_to_database()
    
    # 生成唯一的测试用户信息
    timestamp = datetime.now().timestamp()
    email = f"test_user_{timestamp}@test.com"
    username = f"test_user_{timestamp}"
    password = "Test@Password123"
    
    # 创建用户数据对象
    user_data = UserCreate(
        email=email,
        username=username,
        password=password
    )
    
    # 创建测试用户服务实例并使用mock_mongo
    with patch('app.services.user.mongodb', mock_mongo):
        try:
            # 测试用户创建
            print(f"开始创建测试用户: {email}")
            user = await user_service.create(user_data)
            assert user is not None
            assert user.email == email
            assert user.username == username
            print(f"用户创建成功，ID: {user.id}")
            
            # 测试通过邮箱查找用户
            found_user = await user_service.get_by_email(email)
            assert found_user is not None
            assert found_user.email == email
            print(f"通过邮箱成功查找到用户: {found_user.email}")
            
            # 测试通过用户名查找用户
            found_user = await user_service.get_by_username(username)
            assert found_user is not None
            assert found_user.username == username
            print(f"通过用户名成功查找到用户: {found_user.username}")
            
            # 测试用户认证
            authenticated_user = await user_service.authenticate(email, password)
            assert authenticated_user is not None
            assert authenticated_user.email == email
            print(f"用户认证成功: {authenticated_user.email}")
            
            # 测试用户名认证
            authenticated_user = await user_service.authenticate(username, password)
            assert authenticated_user is not None
            assert authenticated_user.username == username
            print(f"通过用户名认证成功: {authenticated_user.username}")
            
            # 测试错误密码
            auth_failed = await user_service.authenticate(email, "wrong_password")
            assert auth_failed is None
            print("使用错误密码认证失败，符合预期")
            
            # 清理：删除测试用户
            print(f"清理测试用户: {email}")
            await mock_mongo.db.users.delete_one({"email": email})
            
        finally:
            # 确保关闭数据库连接
            await mock_mongo.close_database_connection()

if __name__ == "__main__":
    # 直接运行此文件进行测试
    pytest.main(["-xvs", __file__]) 