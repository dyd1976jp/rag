#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用requests直接测试discover API
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8000/api/v1"
LM_STUDIO_URL = "http://0.0.0.0:1234"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"

def pretty_print_json(data):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    # 测试头信息
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n=== 测试discover端点 ===")
    
    # 1. 测试原始discover端点
    print("\n1. 测试原始discover端点:")
    url = f"{BASE_URL}/llm/discover"
    params = {
        "provider": "lmstudio",
        "url": LM_STUDIO_URL
    }
    print(f"请求URL: {url}")
    print(f"请求参数: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        if response.status_code == 200:
            print("请求成功!")
            try:
                data = response.json()
                pretty_print_json(data)
            except:
                print("返回内容不是有效的JSON")
    except Exception as e:
        print(f"请求过程中出错: {str(e)}")
    
    # 2. 测试新的discover-models端点
    print("\n2. 测试新的discover-models端点:")
    url = f"{BASE_URL}/llm/discover-models"
    print(f"请求URL: {url}")
    print(f"请求参数: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        if response.status_code == 200:
            print("请求成功!")
            try:
                data = response.json()
                pretty_print_json(data)
            except:
                print("返回内容不是有效的JSON")
    except Exception as e:
        print(f"请求过程中出错: {str(e)}")
    
    # 3. 测试直接HTTP GET请求（不使用requests的参数封装）
    print("\n3. 测试直接HTTP GET请求:")
    url = f"{BASE_URL}/llm/discover?provider=lmstudio&url={LM_STUDIO_URL}"
    print(f"请求URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        if response.status_code == 200:
            print("请求成功!")
            try:
                data = response.json()
                pretty_print_json(data)
            except:
                print("返回内容不是有效的JSON")
    except Exception as e:
        print(f"请求过程中出错: {str(e)}")

if __name__ == "__main__":
    main() 