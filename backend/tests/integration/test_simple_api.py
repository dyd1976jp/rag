#!/usr/bin/env python3
"""
简单的API测试
"""

import requests
import json

def test_simple_content():
    """测试简单内容"""
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    
    # 简单的测试内容
    data = {
        "content": "第一章：引言\n\n这是内容。",
        "parent_chunk_size": 100,
        "parent_chunk_overlap": 20,
        "parent_separator": "\n\n",
        "child_chunk_size": 50,
        "child_chunk_overlap": 10,
        "child_separator": "\n"
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        print("发送简单测试请求...")
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ 成功")
            print(f"父内容: {repr(result.get('parentContent', ''))}")
            print(f"子内容数量: {len(result.get('childrenContent', []))}")
        else:
            print("✗ 失败")
            
    except Exception as e:
        print(f"错误: {e}")

def test_health():
    """测试健康检查"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"健康检查: {response.status_code}")
    except Exception as e:
        print(f"健康检查失败: {e}")

if __name__ == "__main__":
    test_health()
    test_simple_content()
