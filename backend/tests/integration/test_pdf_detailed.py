#!/usr/bin/env python3
"""
详细测试PDF文件的分割结果
"""

import requests
import json
import os

def test_pdf_detailed():
    """详细测试PDF文件"""
    
    pdf_path = "/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"✗ PDF文件不存在: {pdf_path}")
        return
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    
    try:
        print("=== 详细测试PDF文件分割 ===")
        
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
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API调用成功")
            
            parent_content = result.get('parentContent', '')
            children_content = result.get('childrenContent', [])
            segments = result.get('segments', [])
            
            print(f"\n=== 分割结果统计 ===")
            print(f"成功状态: {result.get('success')}")
            print(f"总段落数: {result.get('total_segments')}")
            print(f"父内容长度: {len(parent_content)}")
            print(f"父内容换行符数量: {parent_content.count(chr(10))}")
            print(f"子内容数量: {len(children_content)}")
            
            print(f"\n=== 格式检查 ===")
            # 检查换行符保持
            if parent_content.count('\n') > 0:
                print("✓ 父内容保留了换行符")
            else:
                print("✗ 父内容丢失了换行符")
            
            # 检查中文标点符号
            if '：' in parent_content:
                print("✓ 父内容保留了中文冒号")
            else:
                print("✗ 父内容中文冒号被改变")
            
            # 检查子内容分割
            if len(children_content) > 1:
                print(f"✓ 正确分割出 {len(children_content)} 个子内容")
            else:
                print("✗ 子内容分割异常")
            
            print(f"\n=== 父内容预览 ===")
            print("前200字符:")
            print(repr(parent_content[:200]))
            
            print(f"\n=== 子内容预览 ===")
            for i, child in enumerate(children_content[:5]):  # 显示前5个子内容
                print(f"子内容 {i+1} (长度: {len(child)}): {repr(child[:80])}")
            
            if len(children_content) > 5:
                print(f"... 还有 {len(children_content) - 5} 个子内容")
            
            print(f"\n=== 段落结构 ===")
            for i, segment in enumerate(segments[:3]):  # 显示前3个段落
                print(f"段落 {i+1}:")
                print(f"  ID: {segment.get('id')}")
                print(f"  长度: {segment.get('length')}")
                print(f"  子段落数: {len(segment.get('children', []))}")
                print(f"  内容预览: {repr(segment.get('content', '')[:60])}")
                
                for j, child in enumerate(segment.get('children', [])[:2]):
                    print(f"    子段落 {j+1}: {repr(child.get('content', '')[:40])}")
            
            # 一致性检查
            print(f"\n=== 一致性检查 ===")
            total_child_from_segments = sum(len(seg.get('children', [])) for seg in segments)
            if total_child_from_segments == len(children_content):
                print("✓ 段落结构与子内容数量一致")
            else:
                print(f"✗ 段落结构与子内容数量不一致: {total_child_from_segments} vs {len(children_content)}")
                
        else:
            print(f"✗ API调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_detailed()
