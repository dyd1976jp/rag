#!/usr/bin/env python3
"""
统一文档上传API使用示例

演示如何使用统一的文档上传API进行预览和正式上传
"""

import requests
import json
import os
from typing import Dict, Any

class UnifiedDocumentAPI:
    """统一文档上传API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}" if token else None
        }
    
    def preview_document(
        self, 
        file_path: str,
        parent_chunk_size: int = 1024,
        parent_chunk_overlap: int = 200,
        parent_separator: str = "\n\n",
        child_chunk_size: int = 512,
        child_chunk_overlap: int = 50,
        child_separator: str = "\n"
    ) -> Dict[str, Any]:
        """
        预览文档切割结果
        
        Args:
            file_path: 文档文件路径
            parent_chunk_size: 父块大小
            parent_chunk_overlap: 父块重叠
            parent_separator: 父块分隔符
            child_chunk_size: 子块大小
            child_chunk_overlap: 子块重叠
            child_separator: 子块分隔符
            
        Returns:
            预览结果
        """
        url = f"{self.base_url}/api/v1/rag/documents/upload"
        
        with open(file_path, 'rb') as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {
                "parent_chunk_size": parent_chunk_size,
                "parent_chunk_overlap": parent_chunk_overlap,
                "parent_separator": parent_separator,
                "child_chunk_size": child_chunk_size,
                "child_chunk_overlap": child_chunk_overlap,
                "child_separator": child_separator,
                "preview_only": True  # 关键参数：启用预览模式
            }
            
            response = requests.post(url, files=files, data=data, headers=self.headers)
            return response.json()
    
    def upload_document(
        self, 
        file_path: str,
        parent_chunk_size: int = 1024,
        parent_chunk_overlap: int = 200,
        parent_separator: str = "\n\n",
        child_chunk_size: int = 512,
        child_chunk_overlap: int = 50,
        child_separator: str = "\n"
    ) -> Dict[str, Any]:
        """
        正式上传文档
        
        Args:
            file_path: 文档文件路径
            parent_chunk_size: 父块大小
            parent_chunk_overlap: 父块重叠
            parent_separator: 父块分隔符
            child_chunk_size: 子块大小
            child_chunk_overlap: 子块重叠
            child_separator: 子块分隔符
            
        Returns:
            上传结果
        """
        url = f"{self.base_url}/api/v1/rag/documents/upload"
        
        with open(file_path, 'rb') as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {
                "parent_chunk_size": parent_chunk_size,
                "parent_chunk_overlap": parent_chunk_overlap,
                "parent_separator": parent_separator,
                "child_chunk_size": child_chunk_size,
                "child_chunk_overlap": child_chunk_overlap,
                "child_separator": child_separator,
                "preview_only": False  # 关键参数：禁用预览模式，进行正式上传
            }
            
            response = requests.post(url, files=files, data=data, headers=self.headers)
            return response.json()


def print_response_summary(response: Dict[str, Any], mode: str):
    """打印响应摘要"""
    print(f"\n=== {mode}模式响应摘要 ===")
    print(f"成功: {response.get('success')}")
    print(f"消息: {response.get('message')}")
    print(f"预览模式: {response.get('preview_mode')}")
    print(f"文档ID: {response.get('doc_id')}")
    print(f"总段落数: {response.get('total_segments')}")
    print(f"父段落数: {response.get('parent_segments')}")
    print(f"子段落数: {response.get('child_segments')}")
    
    if response.get('document_overview'):
        overview = response['document_overview']
        print(f"文档标题: {overview.get('title')}")
        print(f"文档长度: {overview.get('total_length')}")


def demo_unified_api():
    """演示统一API的使用"""
    # 创建API客户端（需要替换为实际的token）
    api = UnifiedDocumentAPI(token="your_jwt_token_here")
    
    # 创建示例文档
    test_content = """第一章 引言

这是一个测试文档，用于演示统一的文档上传API。
本文档包含多个段落和章节。

第二章 主要内容

这里是主要内容的第一段。
包含了详细的说明和示例。

这是主要内容的第二段。
提供了更多的技术细节。

第三章 结论

通过本文档的演示，我们可以看到：
1. 预览模式和正式上传模式使用相同的API
2. 响应格式完全一致
3. 参数处理逻辑统一

这确保了用户体验的一致性。"""
    
    # 创建临时文件
    test_file = "temp_test_document.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    try:
        print("=== 统一文档上传API演示 ===")
        
        # 1. 预览模式
        print("\n1. 预览文档切割结果...")
        preview_result = api.preview_document(
            file_path=test_file,
            parent_chunk_size=500,
            parent_chunk_overlap=100,
            parent_separator="\n\n",
            child_chunk_size=250,
            child_chunk_overlap=50,
            child_separator="\n"
        )
        print_response_summary(preview_result, "预览")
        
        # 显示切割详情
        if preview_result.get('success') and preview_result.get('segments'):
            print(f"\n预览切割详情:")
            for i, segment in enumerate(preview_result['segments'][:3]):  # 只显示前3个
                print(f"  段落 {i}: {segment['content'][:50]}...")
        
        # 2. 正式上传模式
        print("\n2. 正式上传文档...")
        upload_result = api.upload_document(
            file_path=test_file,
            parent_chunk_size=500,
            parent_chunk_overlap=100,
            parent_separator="\n\n",
            child_chunk_size=250,
            child_chunk_overlap=50,
            child_separator="\n"
        )
        print_response_summary(upload_result, "上传")
        
        # 3. 比较两种模式的响应
        print("\n3. 响应一致性验证:")
        preview_keys = set(preview_result.keys())
        upload_keys = set(upload_result.keys())
        
        if preview_keys == upload_keys:
            print("✅ 响应字段完全一致")
        else:
            print("❌ 响应字段不一致")
            print(f"差异: {preview_keys.symmetric_difference(upload_keys)}")
        
        # 验证内容一致性
        if (preview_result.get('parentContent') == upload_result.get('parentContent') and
            preview_result.get('childrenContent') == upload_result.get('childrenContent')):
            print("✅ 文档内容处理一致")
        else:
            print("❌ 文档内容处理不一致")
        
        print("\n=== 演示完成 ===")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        print("请确保:")
        print("1. 后端服务正在运行 (http://localhost:8000)")
        print("2. 已获取有效的JWT token")
        print("3. 网络连接正常")
    
    finally:
        # 清理临时文件
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == "__main__":
    demo_unified_api()
