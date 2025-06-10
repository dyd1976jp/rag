#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用固定Token测试LLM API
"""

import requests
import json

# 配置
API_URL = "http://localhost:8000"
LM_STUDIO_URL = "http://0.0.0.0:1234"
# 固定的测试Token - 有效期30天
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"

def pretty_print_json(data):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    # 测试头信息
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n=== 测试使用固定Token方式 ===")
    print(f"使用Token: {AUTH_TOKEN[:15]}...")
    
    # 测试1: 获取所有LLM模型
    print("\n1. 获取所有LLM模型")
    all_llms_url = f"{API_URL}/api/v1/llm/"
    try:
        response = requests.get(all_llms_url, headers=headers)
        print(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            print("获取LLM模型成功!")
            data = response.json()
            print(f"模型数量: {len(data)}")
            pretty_print_json(data)
        else:
            print(f"获取LLM模型失败: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求LLM模型时出错: {str(e)}")
    
    # 测试2: 发现LM Studio中的模型
    print("\n2. 发现LM Studio中的模型")
    discover_url = f"{API_URL}/api/v1/llm/discover"
    params = {"provider": "lmstudio", "url": LM_STUDIO_URL}
    
    try:
        response = requests.get(discover_url, params=params, headers=headers)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("发现模型成功!")
            data = response.json()
            print(f"发现模型数量: {len(data)}")
            pretty_print_json(data)
        else:
            print(f"发现模型失败: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求发现模型时出错: {str(e)}")

if __name__ == "__main__":
    main() 