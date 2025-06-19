#!/usr/bin/env python3
"""
测试简单文本内容
"""

import requests
import json

def test_simple_text():
    """测试简单文本内容"""
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    
    # 非常简单的测试内容
    test_content = "第一章\n\n第二章"
    
    data = {
        "content": test_content,
        "parent_chunk_size": 100,
        "parent_chunk_overlap": 20,
        "parent_separator": "\n\n",
        "child_chunk_size": 50,
        "child_chunk_overlap": 10,
        "child_separator": "\n"
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        print("=== 测试简单文本内容 ===")
        print(f"内容: {repr(test_content)}")
        print(f"包含\\n\\n: {chr(10)+chr(10) in test_content}")
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API调用成功")
            print(f"total_segments: {result.get('total_segments')}")
            print(f"childrenContent数量: {len(result.get('childrenContent', []))}")
        else:
            print("✗ API调用失败")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_simple_text()
