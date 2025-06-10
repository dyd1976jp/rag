import pytest
import asyncio
from datetime import datetime
from app.db.mongodb import mongodb
from unittest.mock import patch
from app.services.llm_service import llm_service
from app.schemas.llm import LLMCreate, LLMUpdate

@pytest.mark.asyncio
async def test_llm_crud(mock_mongo):
    """测试LLM模型CRUD操作"""
    await mock_mongo.connect_to_database()
    
    # 生成唯一的测试模型名称
    timestamp = datetime.now().timestamp()
    model_name = f"test_model_{timestamp}"
    
    # 创建测试LLM数据
    llm_data = LLMCreate(
        name=model_name,
        provider="Test Provider",
        model_type="Test Model",
        api_url="http://localhost:8000/test",
        api_key="test_api_key",
        default=False
    )
    
    # 使用模拟MongoDB
    with patch('app.services.llm_service.mongodb', mock_mongo):
        try:
            # 测试创建LLM
            print(f"开始创建测试LLM: {model_name}")
            llm = await llm_service.create_llm(llm_data)
            llm_id = llm.id
            assert llm is not None
            assert llm.name == model_name
            print(f"LLM创建成功，ID: {llm_id}")
            
            # 测试获取LLM
            found_llm = await llm_service.get_llm(llm_id)
            assert found_llm is not None
            assert found_llm.name == model_name
            print(f"成功获取LLM: {found_llm.name}")
            
            # 测试更新LLM
            update_data = LLMUpdate(
                name=f"{model_name}_updated",
                temperature=0.9
            )
            updated_llm = await llm_service.update_llm(llm_id, update_data)
            assert updated_llm is not None
            assert updated_llm.name == f"{model_name}_updated"
            assert updated_llm.temperature == 0.9
            print(f"成功更新LLM: {updated_llm.name}")
            
            # 测试设置为默认
            default_update = LLMUpdate(default=True)
            updated_llm = await llm_service.update_llm(llm_id, default_update)
            assert updated_llm.default == True
            
            # 测试获取默认LLM
            default_llm = await llm_service.get_default_llm()
            assert default_llm is not None
            assert default_llm.id == llm_id
            print(f"成功获取默认LLM: {default_llm.name}")
            
            # 测试获取所有LLM
            all_llms = await llm_service.get_llms()
            assert len(all_llms) > 0
            print(f"获取到 {len(all_llms)} 个LLM")
            
            # 测试删除LLM
            delete_result = await llm_service.delete_llm(llm_id)
            assert delete_result == True
            print(f"成功删除LLM")
            
            # 验证删除结果
            deleted_llm = await llm_service.get_llm(llm_id)
            assert deleted_llm is None
            print(f"验证LLM已删除")
            
        finally:
            # 清理数据库
            await mock_mongo.db.llms.delete_one({"name": model_name})
            await mock_mongo.db.llms.delete_one({"name": f"{model_name}_updated"})
            
            # 关闭数据库连接
            await mock_mongo.close_database_connection()

@pytest.mark.asyncio
async def test_llm_test_functionality(mock_mongo):
    """测试LLM测试功能"""
    # 注意：这个测试可能需要有效的API密钥才能通过
    # 你可以根据实际情况修改此测试或标记为跳过
    
    await mock_mongo.connect_to_database()
    
    # 创建一个假的本地LLM进行测试
    timestamp = datetime.now().timestamp()
    model_name = f"test_model_{timestamp}"
    
    llm_data = LLMCreate(
        name=model_name,
        provider="Local",
        model_type="Test Model",
        api_url="http://localhost:8000/test-db",  # 使用我们之前创建的测试端点
        default=False
    )
    
    # 使用模拟MongoDB
    with patch('app.services.llm_service.mongodb', mock_mongo):
        try:
            # 创建测试LLM
            llm = await llm_service.create_llm(llm_data)
            assert llm is not None
            
            # 测试LLM功能
            print(f"尝试测试LLM: {llm.name}")
            # 注意：这里实际上无法进行真实的LLM测试，除非有可用的API
            # test_result = await llm_service.test_llm(llm.id, "Test prompt")
            # print(f"测试结果: {test_result}")
            
            # 清理：删除测试LLM
            await llm_service.delete_llm(llm.id)
            
        finally:
            # 确保清理
            await mock_mongo.db.llms.delete_one({"name": model_name})
            await mock_mongo.close_database_connection()

if __name__ == "__main__":
    # 直接运行此文件进行测试
    pytest.main(["-xvs", __file__]) 