#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM 发现接口测试脚本
"""

import requests
import json
import os

# 配置
API_URL = "http://localhost:8000"
# 使用新生成的Token
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"
LM_STUDIO_URL = "http://0.0.0.0:1234"  # LM Studio API URL

def pretty_print_json(data):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    # 测试头信息
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 打印调试信息
    print(f"API URL: {API_URL}")
    print(f"LM Studio URL: {LM_STUDIO_URL}")
    print(f"Auth Token: {AUTH_TOKEN[:10]}...")
    
    # 测试LM Studio是否可访问
    print("\n1. 测试LM Studio API")
    try:
        lm_studio_response = requests.get(f"{LM_STUDIO_URL}/v1/models/", timeout=5)
        print(f"LM Studio API状态码: {lm_studio_response.status_code}")
        if lm_studio_response.status_code == 200:
            print("LM Studio API 可以访问")
            data = lm_studio_response.json()
            print(f"可用模型数量: {len(data.get('data', []))}")
            pretty_print_json(data)
        else:
            print(f"LM Studio API返回错误: {lm_studio_response.status_code}")
            print(lm_studio_response.text)
    except Exception as e:
        print(f"无法连接到LM Studio: {str(e)}")
    
    # 测试发现接口
    print("\n2. 测试发现API")
    discover_url = f"{API_URL}/api/v1/llm/discover"
    params = {"provider": "lmstudio", "url": LM_STUDIO_URL}
    
    print(f"请求URL: {discover_url}")
    print(f"请求参数: {params}")
    print(f"请求头: {headers}")
    
    try:
        response = requests.get(
            discover_url,
            params=params,
            headers=headers
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("发现API测试成功!")
            data = response.json()
            print(f"发现模型数量: {len(data)}")
            pretty_print_json(data)
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