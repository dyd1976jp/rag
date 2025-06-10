#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
开发模式下的LLM发现接口测试脚本
"""

import requests
import json

# 配置
API_URL = "http://localhost:8000"
LM_STUDIO_URL = "http://0.0.0.0:1234"  # LM Studio API URL

def pretty_print_json(data):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    # 直接测试发现接口，不使用Token
    print("\n=== 测试开发模式下的LLM发现API ===")
    discover_url = f"{API_URL}/api/v1/llm/discover"
    params = {"provider": "lmstudio", "url": LM_STUDIO_URL}
    
    print(f"请求URL: {discover_url}")
    print(f"请求参数: {params}")
    
    try:
        # 不带认证头发起请求
        response = requests.get(
            discover_url,
            params=params
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("发现API测试成功!")
            data = response.json()
            print(f"发现模型数量: {len(data)}")
            pretty_print_json(data)
            
            # 如果发现了模型，尝试打印第一个模型的详细信息
            if data and len(data) > 0:
                print("\n=== 第一个模型详情 ===")
                pretty_print_json(data[0])
        else:
            print(f"发现API测试失败: {response.status_code}")
            try:
                error = response.json()
                print("错误详情:")
                pretty_print_json(error)
            except:
                print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求发现API时出错: {str(e)}")

if __name__ == "__main__":
    main() 