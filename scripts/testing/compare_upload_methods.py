#!/usr/bin/env python3
"""
对比页面上传和curl命令上传的参数差异分析脚本

此脚本用于分析前端页面文档上传功能与curl命令调用API时的参数差异，
帮助定位导致结果不一致的根本原因。
"""

import json
import requests
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def analyze_frontend_parameters():
    """分析前端页面上传的参数设置"""
    print("=== 前端页面上传参数分析 ===")
    
    # DocumentCollectionDetail.tsx 参数
    print("\n1. DocumentCollectionDetail.tsx 参数:")
    collection_detail_params = {
        'parent_chunk_size': '512',
        'parent_chunk_overlap': '50', 
        'parent_separator': '\\n\\n',
        'child_chunk_size': '256',
        'child_chunk_overlap': '25',
        'child_separator': '\\n',
        'preview_only': 'false'
    }
    for key, value in collection_detail_params.items():
        print(f"  {key}: {value}")
    
    # Documents.tsx 参数 (默认值)
    print("\n2. Documents.tsx 参数 (默认值):")
    chunk_size = 512
    chunk_overlap = 50
    documents_params = {
        'parent_chunk_size': str(chunk_size),
        'parent_chunk_overlap': str(chunk_overlap),
        'parent_separator': '\\n\\n',
        'child_chunk_size': str(chunk_size // 2),  # 256
        'child_chunk_overlap': str(chunk_overlap // 4),  # 12 (注意这里有差异!)
        'child_separator': '\\n',
        'preview_only': 'false'
    }
    for key, value in documents_params.items():
        print(f"  {key}: {value}")
    
    return collection_detail_params, documents_params

def analyze_curl_parameters():
    """分析curl命令的参数设置"""
    print("\n=== curl命令参数分析 ===")
    
    curl_params = {
        'parent_chunk_size': '1024',  # 默认值
        'parent_chunk_overlap': '200',  # 默认值
        'parent_separator': '\\n\\n',  # 默认值
        'child_chunk_size': '512',  # 默认值
        'child_chunk_overlap': '50',  # 默认值
        'child_separator': '\\n',  # 默认值
        'preview_only': 'false'
    }
    
    print("curl命令参数 (API默认值):")
    for key, value in curl_params.items():
        print(f"  {key}: {value}")
    
    return curl_params

def compare_parameters():
    """对比参数差异"""
    print("\n=== 参数差异对比 ===")
    
    collection_params, documents_params = analyze_frontend_parameters()
    curl_params = analyze_curl_parameters()
    
    print("\n1. DocumentCollectionDetail.tsx vs curl命令:")
    for key in collection_params:
        if key in curl_params:
            frontend_val = collection_params[key]
            curl_val = curl_params[key]
            if frontend_val != curl_val:
                print(f"  ❌ {key}: 前端={frontend_val}, curl={curl_val}")
            else:
                print(f"  ✅ {key}: {frontend_val}")
    
    print("\n2. Documents.tsx vs curl命令:")
    for key in documents_params:
        if key in curl_params:
            frontend_val = documents_params[key]
            curl_val = curl_params[key]
            if frontend_val != curl_val:
                print(f"  ❌ {key}: 前端={frontend_val}, curl={curl_val}")
            else:
                print(f"  ✅ {key}: {frontend_val}")
    
    print("\n3. 两个前端页面之间的差异:")
    for key in collection_params:
        if key in documents_params:
            val1 = collection_params[key]
            val2 = documents_params[key]
            if val1 != val2:
                print(f"  ❌ {key}: DocumentCollectionDetail={val1}, Documents={val2}")
            else:
                print(f"  ✅ {key}: {val1}")

def analyze_api_defaults():
    """分析API端点的默认参数"""
    print("\n=== API端点默认参数分析 ===")
    
    # 从后端代码中提取的默认值
    api_defaults = {
        'parent_chunk_size': 1024,
        'parent_chunk_overlap': 200,
        'parent_separator': '\\n\\n',
        'child_chunk_size': 512,
        'child_chunk_overlap': 50,
        'child_separator': '\\n',
        'preview_only': False
    }
    
    print("API端点默认参数:")
    for key, value in api_defaults.items():
        print(f"  {key}: {value}")
    
    return api_defaults

def generate_test_commands():
    """生成测试命令"""
    print("\n=== 生成测试命令 ===")
    
    test_file = "/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.txt"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0MkBleGFtcGxlLmNvbSIsImV4cCI6MTc1MTA2ODkzMX0.hK1ZSzjW12z6NXmipmmo-tvJqBel4W7U5jwoU_5DArI"
    
    # 模拟DocumentCollectionDetail.tsx的参数
    print("\n1. 模拟DocumentCollectionDetail.tsx参数的curl命令:")
    cmd1 = f'''curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \\
  -H "Authorization: Bearer {token}" \\
  -F "file=@{test_file}" \\
  -F "parent_chunk_size=512" \\
  -F "parent_chunk_overlap=50" \\
  -F "parent_separator=\\n\\n" \\
  -F "child_chunk_size=256" \\
  -F "child_chunk_overlap=25" \\
  -F "child_separator=\\n" \\
  -F "preview_only=false"'''
    print(cmd1)
    
    # 模拟Documents.tsx的参数
    print("\n2. 模拟Documents.tsx参数的curl命令:")
    cmd2 = f'''curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \\
  -H "Authorization: Bearer {token}" \\
  -F "file=@{test_file}" \\
  -F "parent_chunk_size=512" \\
  -F "parent_chunk_overlap=50" \\
  -F "parent_separator=\\n\\n" \\
  -F "child_chunk_size=256" \\
  -F "child_chunk_overlap=12" \\
  -F "child_separator=\\n" \\
  -F "preview_only=false"'''
    print(cmd2)
    
    # 原始curl命令（使用API默认值）
    print("\n3. 原始curl命令（API默认值）:")
    cmd3 = f'''curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \\
  -H "Authorization: Bearer {token}" \\
  -F "file=@{test_file}" \\
  -F "preview_only=false"'''
    print(cmd3)

def main():
    """主函数"""
    print("页面上传与curl命令参数差异分析")
    print("=" * 50)
    
    # 分析参数差异
    compare_parameters()
    
    # 分析API默认参数
    analyze_api_defaults()
    
    # 生成测试命令
    generate_test_commands()
    
    print("\n=== 分析总结 ===")
    print("发现的主要差异:")
    print("1. 前端页面使用的chunk_size参数与curl命令(API默认值)不同")
    print("   - 前端: parent_chunk_size=512, child_chunk_size=256")
    print("   - curl: parent_chunk_size=1024, child_chunk_size=512")
    print("2. Documents.tsx中child_chunk_overlap计算可能有问题:")
    print("   - 计算值: 50//4=12")
    print("   - DocumentCollectionDetail.tsx中硬编码为25")
    print("3. 这些参数差异可能导致文档分块结果不同，进而影响存储到数据库的内容")

if __name__ == "__main__":
    main()
