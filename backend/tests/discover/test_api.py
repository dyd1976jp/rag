#!/usr/bin/env python
"""
API测试脚本

用于测试后端API端点，特别是模型发现功能
"""

import httpx
import asyncio
import json
from pprint import pprint

# 常量定义
API_URL = "http://localhost:8000"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzQ4MjYyNzUwfQ.x9vEcvY7OsoTVMmQTL8I4cqV2Cm8RjLqi61jI4lYZEg"

async def test_discover_models():
    """测试模型发现API"""
    print("\n=== 测试模型发现API ===")
    
    # 定义API端点和参数
    endpoint = f"{API_URL}/api/v1/llm/discover-models"
    params = {
        "provider": "lmstudio",
        "url": "http://localhost:1234"  # 确保使用正确的URL格式
    }
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"请求URL: {endpoint}")
    print(f"请求参数: {params}")
    print(f"请求头: {headers}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            
            if response.status_code == 200:
                result = response.json()
                print("响应内容:")
                pprint(result)
                return result
            else:
                print(f"错误响应: {response.text}")
                return None
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

async def main():
    """主函数"""
    # 测试模型发现API
    await test_discover_models()

if __name__ == "__main__":
    asyncio.run(main()) 