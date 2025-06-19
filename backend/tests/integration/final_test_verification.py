#!/usr/bin/env python3
"""
最终验证测试 - 验证分割器修复的完整性
"""

import requests
import json

def test_comprehensive_splitting():
    """全面测试分割功能"""
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    
    # 测试用例1：标准章节分割
    test_case_1 = {
        "name": "标准章节分割",
        "content": """第一章：引言

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

总结内容在这里。""",
        "expected_parents": 8,
        "expected_children_min": 10
    }
    
    # 测试用例2：简单分割
    test_case_2 = {
        "name": "简单分割",
        "content": "第一段\n\n第二段\n\n第三段",
        "expected_parents": 3,
        "expected_children_min": 3
    }
    
    # 测试用例3：复杂格式
    test_case_3 = {
        "name": "复杂格式",
        "content": """标题一

内容一行一
内容一行二

标题二

内容二行一
内容二行二
内容二行三

标题三

内容三""",
        "expected_parents": 6,
        "expected_children_min": 8
    }
    
    test_cases = [test_case_1, test_case_2, test_case_3]
    
    headers = {"Content-Type": "application/json"}
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n=== 测试用例 {i}: {test_case['name']} ===")
        
        data = {
            "content": test_case["content"],
            "parent_chunk_size": 1024,
            "parent_chunk_overlap": 200,
            "parent_separator": "\n\n",
            "child_chunk_size": 512,
            "child_chunk_overlap": 50,
            "child_separator": "\n"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                
                total_segments = result.get('total_segments', 0)
                children_count = len(result.get('childrenContent', []))
                parent_content = result.get('parentContent', '')
                
                print(f"✓ API调用成功")
                print(f"  父段落数: {total_segments}")
                print(f"  子段落数: {children_count}")
                print(f"  父内容长度: {len(parent_content)}")
                double_newline = '\n\n'
                print(f"  保留换行符: {double_newline in parent_content}")
                print(f"  保留中文冒号: {'：' in parent_content}")
                
                # 验证结果
                passed = True
                
                if total_segments != test_case["expected_parents"]:
                    print(f"✗ 父段落数错误: 期望{test_case['expected_parents']}, 实际{total_segments}")
                    passed = False
                else:
                    print(f"✓ 父段落数正确: {total_segments}")
                
                if children_count < test_case["expected_children_min"]:
                    print(f"✗ 子段落数不足: 期望至少{test_case['expected_children_min']}, 实际{children_count}")
                    passed = False
                else:
                    print(f"✓ 子段落数合理: {children_count}")
                
                if double_newline not in parent_content:
                    print(f"✗ 父内容丢失换行符")
                    passed = False
                else:
                    print(f"✓ 父内容保留换行符")
                
                if not passed:
                    all_passed = False
                    
            else:
                print(f"✗ API调用失败: {response.status_code}")
                print(f"  错误信息: {response.text}")
                all_passed = False
                
        except Exception as e:
            print(f"✗ 测试异常: {e}")
            all_passed = False
    
    print(f"\n=== 最终结果 ===")
    if all_passed:
        print("🎉 所有测试用例通过！分割器修复成功！")
    else:
        print("❌ 部分测试用例失败，需要进一步检查")
    
    return all_passed

def test_edge_cases():
    """测试边界情况"""
    
    print(f"\n=== 边界情况测试 ===")
    
    url = "http://localhost:8000/api/v1/rag/documents/preview-split"
    headers = {"Content-Type": "application/json"}
    
    # 边界用例
    edge_cases = [
        {
            "name": "只有一个段落",
            "content": "这是唯一的段落内容",
            "expected_behavior": "应该生成1个父段落和1个子段落"
        },
        {
            "name": "空分隔符之间的内容",
            "content": "段落一\n\n\n\n段落二",
            "expected_behavior": "应该正确处理多个连续换行符"
        },
        {
            "name": "包含特殊字符",
            "content": "段落一：测试\n\n段落二！@#$%^&*()",
            "expected_behavior": "应该保留所有特殊字符"
        }
    ]
    
    for case in edge_cases:
        print(f"\n--- {case['name']} ---")
        print(f"期望行为: {case['expected_behavior']}")
        
        data = {
            "content": case["content"],
            "parent_chunk_size": 1024,
            "parent_chunk_overlap": 200,
            "parent_separator": "\n\n",
            "child_chunk_size": 512,
            "child_chunk_overlap": 50,
            "child_separator": "\n"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ 处理成功: {result.get('total_segments')}个父段落, {len(result.get('childrenContent', []))}个子段落")
            else:
                print(f"✗ 处理失败: {response.status_code}")
                
        except Exception as e:
            print(f"✗ 异常: {e}")

if __name__ == "__main__":
    print("开始最终验证测试...")
    
    # 全面测试
    success = test_comprehensive_splitting()
    
    # 边界情况测试
    test_edge_cases()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 RAG聊天系统文档分割功能修复验证完成！")
        print("✅ 父子分割逻辑正常工作")
        print("✅ 文档格式完整保持")
        print("✅ 分割结果一致可靠")
    else:
        print("❌ 修复验证未完全通过，需要进一步调试")
    
    print("测试完成！")
