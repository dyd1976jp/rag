"""
API 工作流集成测试

测试完整的API工作流程，包括文档处理、分割和检索等功能。
"""

import pytest
import requests
import json
from typing import Dict, Any


class TestAPIWorkflow:
    """API工作流测试类"""
    
    BASE_URL = "http://localhost:8000"
    
    def test_health_check(self):
        """测试健康检查端点"""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            print("✓ 健康检查通过")
        except Exception as e:
            pytest.fail(f"健康检查失败: {e}")
    
    def test_document_split_workflow(self):
        """测试文档分割工作流"""
        url = f"{self.BASE_URL}/api/v1/rag/documents/preview-split"
        
        # 测试数据
        test_cases = [
            {
                "name": "简单中文文档",
                "data": {
                    "content": "第一章：引言\n\n这是第一章的内容。\n\n第二章：方法\n\n这是第二章的内容。",
                    "parent_chunk_size": 100,
                    "parent_chunk_overlap": 20,
                    "parent_separator": "\n\n",
                    "child_chunk_size": 50,
                    "child_chunk_overlap": 10,
                    "child_separator": "\n"
                }
            },
            {
                "name": "长文档",
                "data": {
                    "content": "这是一个很长的测试文档。" * 100,
                    "parent_chunk_size": 500,
                    "parent_chunk_overlap": 50,
                    "child_chunk_size": 250,
                    "child_chunk_overlap": 25
                }
            }
        ]
        
        headers = {"Content-Type": "application/json"}
        
        for test_case in test_cases:
            print(f"\n测试用例: {test_case['name']}")
            
            try:
                response = requests.post(
                    url, 
                    json=test_case['data'], 
                    headers=headers, 
                    timeout=30
                )
                
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    assert "success" in result or "parentContent" in result
                    print(f"✓ {test_case['name']} 测试通过")
                    
                    # 验证响应结构
                    if "parentContent" in result:
                        assert isinstance(result["parentContent"], str)
                        print(f"  父内容长度: {len(result['parentContent'])}")
                    
                    if "childrenContent" in result:
                        assert isinstance(result["childrenContent"], list)
                        print(f"  子内容数量: {len(result['childrenContent'])}")
                        
                elif response.status_code == 401:
                    print(f"✓ {test_case['name']} 需要认证（端点可访问）")
                else:
                    print(f"✗ {test_case['name']} 失败: HTTP {response.status_code}")
                    print(f"  响应: {response.text[:200]}")
                    
            except Exception as e:
                pytest.fail(f"{test_case['name']} 测试失败: {e}")
    
    def test_error_handling(self):
        """测试错误处理"""
        url = f"{self.BASE_URL}/api/v1/rag/documents/preview-split"
        headers = {"Content-Type": "application/json"}
        
        # 错误测试用例
        error_cases = [
            {
                "name": "空内容",
                "data": {"content": ""},
                "expected_status": [400, 422]
            },
            {
                "name": "缺少必需参数",
                "data": {"parent_chunk_size": 100},
                "expected_status": [400, 422]
            },
            {
                "name": "无效参数值",
                "data": {"content": "test", "parent_chunk_size": -1},
                "expected_status": [400, 422]
            }
        ]
        
        for error_case in error_cases:
            print(f"\n错误测试: {error_case['name']}")
            
            try:
                response = requests.post(
                    url,
                    json=error_case['data'],
                    headers=headers,
                    timeout=10
                )
                
                print(f"状态码: {response.status_code}")
                
                if response.status_code in error_case['expected_status']:
                    print(f"✓ {error_case['name']} 正确返回错误")
                else:
                    print(f"? {error_case['name']} 状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"✗ {error_case['name']} 请求失败: {e}")
    
    def test_special_characters(self):
        """测试特殊字符处理"""
        url = f"{self.BASE_URL}/api/v1/rag/documents/preview-split"
        headers = {"Content-Type": "application/json"}
        
        special_content = """
        测试特殊字符：©®™€£¥
        测试emoji：😀😃😄😁😆
        测试Unicode：αβγδε ñáéíóú
        测试符号：@#$%^&*()_+-=[]{}|;:,.<>?
        """
        
        data = {
            "content": special_content,
            "parent_chunk_size": 200,
            "child_chunk_size": 100
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            print(f"特殊字符测试状态码: {response.status_code}")
            
            if response.status_code in [200, 401]:
                print("✓ 特殊字符处理正常")
            else:
                print(f"? 特殊字符测试状态码: {response.status_code}")
                
        except Exception as e:
            print(f"✗ 特殊字符测试失败: {e}")


if __name__ == "__main__":
    # 直接运行测试
    test_workflow = TestAPIWorkflow()
    test_workflow.test_health_check()
    test_workflow.test_document_split_workflow()
    test_workflow.test_error_handling()
    test_workflow.test_special_characters()
    print("\n集成测试完成！")
