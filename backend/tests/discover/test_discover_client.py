#!/usr/bin/env python
"""
模型发现API测试客户端

用于测试模型发现的API端点
"""

import asyncio
import httpx
from pprint import pprint

# 配置信息
API_URL = "http://localhost:8000"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzQ4MjYyNzUwfQ.x9vEcvY7OsoTVMmQTL8I4cqV2Cm8RjLqi61jI4lYZEg"

# 测试参数
TEST_PROVIDER = "lmstudio"  # 测试的提供商
TEST_URL = "http://localhost:1234"  # LM Studio的URL

async def test_discover_models():
    """测试模型发现API"""
    print("\n===== 测试模型发现API =====")
    
    # API端点和参数
    endpoint = f"{API_URL}/api/v1/discover/"
    params = {
        "provider": TEST_PROVIDER,
        "url": TEST_URL
    }
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"请求URL: {endpoint}")
    print(f"请求参数: {params}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            print(f"响应状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("\n发现的模型:")
                for i, model in enumerate(result, 1):
                    print(f"[{i}] {model.get('name')} (ID: {model.get('id')})")
                    print(f"    提供商: {model.get('provider')}")
                    print(f"    API URL: {model.get('api_url')}")
                    print(f"    已注册: {'是' if model.get('is_registered') else '否'}")
                    print(f"    上下文窗口: {model.get('context_window')}")
                    print(f"    描述: {model.get('description')}")
                    print("")
                return result
            else:
                print(f"错误响应: {response.text}")
                return None
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

async def test_register_model(model_data):
    """测试注册模型API"""
    if not model_data or not isinstance(model_data, list) or len(model_data) == 0:
        print("没有可用的模型数据进行注册测试")
        return None
    
    print("\n===== 测试注册模型API =====")
    
    # 选择第一个模型进行注册
    model = model_data[0]
    model_id = model.get("id")
    
    # API端点和参数
    endpoint = f"{API_URL}/api/v1/discover/register"
    data = {
        "llm_model_id": model_id,
        "provider": model.get("provider", "Local"),
        "name": f"测试 - {model_id}",
        "api_url": model.get("api_url"),
        "description": f"通过测试脚本注册的{model_id}模型",
        "context_window": model.get("context_window", 8192),
        "set_as_default": False
    }
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"请求URL: {endpoint}")
    print(f"请求数据: {data}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=data,
                headers=headers,
                timeout=30.0
            )
            
            print(f"响应状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("\n注册结果:")
                print(f"ID: {result.get('id')}")
                print(f"名称: {result.get('name')}")
                print(f"提供商: {result.get('provider')}")
                print(f"模型类型: {result.get('model_type')}")
                print(f"API URL: {result.get('api_url')}")
                print(f"状态: {result.get('status')}")
                print(f"是否默认: {'是' if result.get('default') else '否'}")
                return result
            else:
                print(f"错误响应: {response.text}")
                return None
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

async def main():
    """主函数"""
    # 测试模型发现
    discovered_models = await test_discover_models()
    
    # 是否测试注册模型
    if discovered_models:
        print("\n是否要测试注册模型? (y/n)")
        choice = input().strip().lower()
        if choice == 'y':
            await test_register_model(discovered_models)

if __name__ == "__main__":
    asyncio.run(main()) 