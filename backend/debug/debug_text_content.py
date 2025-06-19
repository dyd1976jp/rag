#!/usr/bin/env python3
"""
调试文本内容分割
"""

import requests
import json

def debug_text_content():
    """调试文本内容分割"""
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    
    # 测试内容 - 包含明确的\n\n分隔符
    test_content = """第一章：引言

这是第一章的内容。
它包含多行文本。

第二章：方法

这是第二章的内容。
包含了详细的方法描述。

第三章：结果

实验结果如下：
1. 结果一
2. 结果二
3. 结果三

第四章：总结

总结内容在这里。"""

    data = {
        "content": test_content,
        "parent_chunk_size": 1024,
        "parent_chunk_overlap": 200,
        "parent_separator": "\n\n",
        "child_chunk_size": 512,
        "child_chunk_overlap": 50,
        "child_separator": "\n"
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        print("=== 发送文本内容测试 ===")
        print(f"原始内容长度: {len(test_content)}")
        double_newline = '\n\n'
        print(f"包含\\n\\n: {double_newline in test_content}")
        print(f"\\n\\n数量: {test_content.count(chr(10)+chr(10))}")
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API调用成功")
            
            parent_content = result.get('parentContent', '')
            children_content = result.get('childrenContent', [])
            segments = result.get('segments', [])
            
            print(f"\n=== API返回内容分析 ===")
            print(f"成功状态: {result.get('success')}")
            print(f"总段落数: {result.get('total_segments')}")
            print(f"父内容长度: {len(parent_content)}")
            print(f"父内容包含\\n\\n: {double_newline in parent_content}")
            print(f"父内容\\n\\n数量: {parent_content.count(chr(10)+chr(10))}")
            print(f"子内容数量: {len(children_content)}")
            
            print(f"\n=== 父内容预览 ===")
            print(repr(parent_content[:200]))
            
            print(f"\n=== 段落结构 ===")
            for i, segment in enumerate(segments[:3]):
                print(f"段落 {i+1}:")
                print(f"  ID: {segment.get('id')}")
                print(f"  长度: {segment.get('length')}")
                print(f"  子段落数: {len(segment.get('children', []))}")
                print(f"  内容预览: {repr(segment.get('content', '')[:60])}")
            
            # 手动分割测试
            print(f"\n=== 手动分割测试 ===")
            if '\n\n' in parent_content:
                manual_chunks = parent_content.split('\n\n')
                manual_chunks = [chunk.strip() for chunk in manual_chunks if chunk.strip()]
                print(f"手动父级分割结果: {len(manual_chunks)} 个块")
                
                total_manual_children = 0
                for i, chunk in enumerate(manual_chunks):
                    child_chunks = chunk.split('\n')
                    child_chunks = [c.strip() for c in child_chunks if c.strip()]
                    total_manual_children += len(child_chunks)
                    print(f"  父块 {i+1} (长度: {len(chunk)}): {len(child_chunks)} 个子块")
                
                print(f"手动子级分割总数: {total_manual_children}")
            else:
                print("父内容中不包含\\n\\n分隔符")
                
        else:
            print(f"✗ API调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    debug_text_content()
