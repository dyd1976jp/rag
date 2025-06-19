#!/usr/bin/env python3
"""
调试PDF内容
"""

import requests
import os

def debug_pdf_content():
    """调试PDF内容"""
    
    pdf_path = "/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"✗ PDF文件不存在: {pdf_path}")
        return
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            data = {
                'parent_chunk_size': 1024,
                'parent_chunk_overlap': 200,
                'parent_separator': '\n\n',
                'child_chunk_size': 512,
                'child_chunk_overlap': 50,
                'child_separator': '\n'
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            parent_content = result.get('parentContent', '')
            
            print("=== PDF内容分析 ===")
            print(f"内容长度: {len(parent_content)}")
            double_newline = '\n\n'
            print(f"包含\\n\\n: {double_newline in parent_content}")
            print(f"\\n\\n数量: {parent_content.count(chr(10)+chr(10))}")
            print(f"\\n数量: {parent_content.count(chr(10))}")
            
            print("\n=== 内容预览 ===")
            print(repr(parent_content))
            
            print("\n=== 手动分割测试 ===")
            if '\n\n' in parent_content:
                manual_chunks = parent_content.split('\n\n')
                manual_chunks = [chunk.strip() for chunk in manual_chunks if chunk.strip()]
                print(f"手动分割结果: {len(manual_chunks)} 个块")
                for i, chunk in enumerate(manual_chunks):
                    print(f"块 {i+1} (长度: {len(chunk)}): {repr(chunk[:50])}")
            else:
                print("内容中不包含\\n\\n分隔符")
                
        else:
            print(f"API调用失败: {response.status_code}")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    debug_pdf_content()
