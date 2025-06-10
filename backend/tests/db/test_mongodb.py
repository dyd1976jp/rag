import pytest
import asyncio
from bson import ObjectId
from datetime import datetime
from app.db.mongodb import mongodb
from app.core.config import settings

@pytest.mark.asyncio
async def test_mongodb_connection(mock_mongo):
    """测试MongoDB连接"""
    # 使用模拟对象
    await mock_mongo.connect_to_database()
    assert mock_mongo.db is not None
    
    # 获取数据库名称
    db_info = await mock_mongo.db.command("buildinfo")
    print(f"MongoDB版本: {db_info.get('version')}")
    print(f"数据库名称: mock_db")
    
    # 列出所有集合
    collections = await mock_mongo.db.list_collection_names()
    print(f"当前集合: {collections}")
    
    await mock_mongo.close_database_connection()

@pytest.mark.asyncio
async def test_user_collection(mock_mongo):
    """测试用户集合操作"""
    await mock_mongo.connect_to_database()
    
    # 获取users集合
    users_collection = mock_mongo.db.users
    
    # 创建测试用户
    test_user = {
        "email": f"test_user_{datetime.now().timestamp()}@test.com",
        "username": f"test_user_{datetime.now().timestamp()}",
        "hashed_password": "test_password_hash",
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # 插入测试用户
    result = await users_collection.insert_one(test_user)
    user_id = result.inserted_id
    assert user_id is not None
    print(f"已创建测试用户，ID: {user_id}")
    
    # 查询刚插入的用户
    inserted_user = await users_collection.find_one({"_id": user_id})
    assert inserted_user is not None
    print(f"查询到测试用户: {inserted_user['email']}")
    
    # 更新测试用户
    update_result = await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"is_active": False}}
    )
    assert update_result.modified_count == 1
    print(f"已更新测试用户")
    
    # 删除测试用户
    delete_result = await users_collection.delete_one({"_id": user_id})
    assert delete_result.deleted_count == 1
    print(f"已删除测试用户")
    
    await mock_mongo.close_database_connection()

if __name__ == "__main__":
    # 直接运行此文件进行测试
    pytest.main(["-xvs", __file__]) 