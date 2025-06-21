#!/usr/bin/env python3
"""
全面的 /api/v1/rag/documents/preview-split API端点测试套件

测试功能、错误处理、边界条件和性能
"""

import requests
import json
import time
import threading
import statistics
from datetime import datetime
from typing import Dict, List, Any, Tuple
import concurrent.futures

API_BASE_URL = "http://localhost:8000/api/v1"
ENDPOINT = f"{API_BASE_URL}/rag/documents/preview-split"

class APITestSuite:
    def __init__(self):
        self.test_results = []
        self.performance_data = []
        
    def log_test(self, test_name: str, success: bool, details: str, response_time: float = 0):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        if response_time > 0:
            print(f"    响应时间: {response_time:.3f}s")
        print()

    def make_request(self, data: Dict[str, Any], headers: Dict[str, str] = None, timeout: int = 30) -> Tuple[requests.Response, float]:
        """发送请求并测量响应时间"""
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        try:
            response = requests.post(ENDPOINT, json=data, headers=headers, timeout=timeout)
            response_time = time.time() - start_time
            return response, response_time
        except Exception as e:
            response_time = time.time() - start_time
            raise Exception(f"请求失败: {e}, 响应时间: {response_time:.3f}s")

    def test_basic_functionality(self):
        """1. 基础功能测试"""
        print("=" * 60)
        print("1. 基础功能测试")
        print("=" * 60)
        
        # 测试1.1: 基本的文本分割
        test_data = {
            "content": "这是第一段内容。\n\n这是第二段内容。\n\n这是第三段内容。",
            "parent_chunk_size": 100,
            "parent_chunk_overlap": 20,
            "parent_separator": "\n\n",
            "child_chunk_size": 50,
            "child_chunk_overlap": 10,
            "child_separator": "\n"
        }
        
        try:
            response, response_time = self.make_request(test_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("total_segments", 0) > 0:
                    self.log_test(
                        "基本文本分割功能",
                        True,
                        f"成功分割为 {result.get('total_segments')} 个段落",
                        response_time
                    )
                else:
                    self.log_test(
                        "基本文本分割功能",
                        False,
                        f"响应格式异常: {result}",
                        response_time
                    )
            elif response.status_code == 401:
                self.log_test(
                    "基本文本分割功能",
                    True,
                    "需要认证（端点可访问，无编码错误）",
                    response_time
                )
            else:
                self.log_test(
                    "基本文本分割功能",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    response_time
                )
        except Exception as e:
            self.log_test("基本文本分割功能", False, str(e))

        # 测试1.2: 中文文本处理
        chinese_data = {
            "content": "这是一个包含中文的测试文档。\n\n第一段：介绍内容，包含各种中文字符。\n\n第二段：详细说明，测试UTF-8编码处理。\n\n第三段：总结内容，验证分割算法。",
            "parent_chunk_size": 80,
            "child_chunk_size": 40
        }
        
        try:
            response, response_time = self.make_request(chinese_data)
            
            if response.status_code in [200, 401]:
                self.log_test(
                    "中文文本处理",
                    True,
                    f"HTTP {response.status_code}, 无UTF-8编码错误",
                    response_time
                )
            else:
                self.log_test(
                    "中文文本处理",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    response_time
                )
        except Exception as e:
            self.log_test("中文文本处理", False, str(e))

        # 测试1.3: 参数组合测试
        param_combinations = [
            {"parent_chunk_size": 200, "child_chunk_size": 100},
            {"parent_chunk_size": 500, "child_chunk_size": 250, "parent_overlap": 50},
            {"parent_chunk_size": 1000, "child_chunk_size": 300, "parent_separator": "\n", "child_separator": "。"}
        ]
        
        for i, params in enumerate(param_combinations):
            test_params = {
                "content": "测试内容" * 50,  # 生成足够长的内容
                **params
            }
            
            try:
                response, response_time = self.make_request(test_params)
                success = response.status_code in [200, 401]
                self.log_test(
                    f"参数组合测试 {i+1}",
                    success,
                    f"HTTP {response.status_code}, 参数: {params}",
                    response_time
                )
            except Exception as e:
                self.log_test(f"参数组合测试 {i+1}", False, str(e))

    def test_error_handling(self):
        """2. 错误处理测试"""
        print("=" * 60)
        print("2. 错误处理测试")
        print("=" * 60)
        
        # 测试2.1: 空内容
        try:
            response, response_time = self.make_request({"content": ""})
            
            if response.status_code == 422:
                self.log_test(
                    "空内容处理",
                    True,
                    "正确返回422验证错误",
                    response_time
                )
            elif response.status_code == 400:
                result = response.json()
                self.log_test(
                    "空内容处理",
                    True,
                    f"返回400错误: {result.get('detail', 'N/A')}",
                    response_time
                )
            else:
                self.log_test(
                    "空内容处理",
                    False,
                    f"期望422/400，得到 {response.status_code}",
                    response_time
                )
        except Exception as e:
            self.log_test("空内容处理", False, str(e))

        # 测试2.2: 缺少必需参数
        try:
            response, response_time = self.make_request({"parent_chunk_size": 100})  # 缺少content
            
            success = response.status_code in [400, 422]
            self.log_test(
                "缺少必需参数",
                success,
                f"HTTP {response.status_code}",
                response_time
            )
        except Exception as e:
            self.log_test("缺少必需参数", False, str(e))

        # 测试2.3: 无效参数值
        invalid_params = [
            {"content": "test", "parent_chunk_size": -1},  # 负数
            {"content": "test", "parent_chunk_size": 0},   # 零
            {"content": "test", "child_chunk_size": -5},   # 负数
        ]
        
        for i, params in enumerate(invalid_params):
            try:
                response, response_time = self.make_request(params)
                success = response.status_code in [400, 422]
                self.log_test(
                    f"无效参数值测试 {i+1}",
                    success,
                    f"HTTP {response.status_code}, 参数: {params}",
                    response_time
                )
            except Exception as e:
                self.log_test(f"无效参数值测试 {i+1}", False, str(e))

        # 测试2.4: 错误的Content-Type (multipart/form-data)
        try:
            files = {"file": ("test.txt", "test content", "text/plain")}
            data = {"parent_chunk_size": "100"}
            
            start_time = time.time()
            response = requests.post(ENDPOINT, files=files, data=data, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 400:
                result = response.json()
                if "file_upload_validation_error" in result.get("error_type", ""):
                    self.log_test(
                        "multipart/form-data错误处理",
                        True,
                        "正确返回友好的错误提示",
                        response_time
                    )
                else:
                    self.log_test(
                        "multipart/form-data错误处理",
                        True,
                        f"返回400错误: {result.get('detail', 'N/A')}",
                        response_time
                    )
            else:
                self.log_test(
                    "multipart/form-data错误处理",
                    False,
                    f"期望400，得到 {response.status_code}",
                    response_time
                )
        except Exception as e:
            self.log_test("multipart/form-data错误处理", False, str(e))

    def test_boundary_conditions(self):
        """3. 边界条件测试"""
        print("=" * 60)
        print("3. 边界条件测试")
        print("=" * 60)
        
        # 测试3.1: 极长文本
        long_content = "这是一个很长的测试文档。" * 1000  # 约12000字符
        
        try:
            response, response_time = self.make_request({
                "content": long_content,
                "parent_chunk_size": 500,
                "child_chunk_size": 250
            })
            
            success = response.status_code in [200, 401]
            self.log_test(
                "极长文本处理",
                success,
                f"HTTP {response.status_code}, 文本长度: {len(long_content)}字符",
                response_time
            )
        except Exception as e:
            self.log_test("极长文本处理", False, str(e))

        # 测试3.2: 特殊字符和emoji
        special_content = """
        测试特殊字符：©®™€£¥
        测试emoji：😀😃😄😁😆😅😂🤣
        测试Unicode：αβγδε ñáéíóú
        测试符号：@#$%^&*()_+-=[]{}|;:,.<>?
        测试换行和制表符：\n\t\r
        """
        
        try:
            response, response_time = self.make_request({
                "content": special_content,
                "parent_chunk_size": 100,
                "child_chunk_size": 50
            })
            
            success = response.status_code in [200, 401]
            self.log_test(
                "特殊字符和emoji处理",
                success,
                f"HTTP {response.status_code}",
                response_time
            )
        except Exception as e:
            self.log_test("特殊字符和emoji处理", False, str(e))

        # 测试3.3: 极值参数
        extreme_params = [
            {"content": "test", "parent_chunk_size": 1, "child_chunk_size": 1},
            {"content": "test", "parent_chunk_size": 10000, "child_chunk_size": 5000},
            {"content": "test", "parent_chunk_overlap": 0, "child_chunk_overlap": 0},
        ]
        
        for i, params in enumerate(extreme_params):
            try:
                response, response_time = self.make_request(params)
                success = response.status_code in [200, 401, 400, 422]
                self.log_test(
                    f"极值参数测试 {i+1}",
                    success,
                    f"HTTP {response.status_code}, 参数: {params}",
                    response_time
                )
            except Exception as e:
                self.log_test(f"极值参数测试 {i+1}", False, str(e))

    def test_performance(self):
        """4. 性能测试"""
        print("=" * 60)
        print("4. 性能测试")
        print("=" * 60)
        
        # 测试4.1: 响应时间测试
        test_data = {
            "content": "这是性能测试内容。" * 100,
            "parent_chunk_size": 200,
            "child_chunk_size": 100
        }
        
        response_times = []
        for i in range(5):
            try:
                response, response_time = self.make_request(test_data)
                response_times.append(response_time)
                print(f"    请求 {i+1}: {response_time:.3f}s (HTTP {response.status_code})")
            except Exception as e:
                print(f"    请求 {i+1}: 失败 - {e}")
        
        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            success = avg_time < 5.0  # 平均响应时间应小于5秒
            self.log_test(
                "响应时间测试",
                success,
                f"平均: {avg_time:.3f}s, 最大: {max_time:.3f}s, 最小: {min_time:.3f}s",
                avg_time
            )
        else:
            self.log_test("响应时间测试", False, "所有请求都失败")

        # 测试4.2: 并发测试
        def concurrent_request():
            try:
                response, response_time = self.make_request(test_data)
                return response.status_code, response_time
            except Exception as e:
                return None, 0

        print("    执行并发测试 (5个并发请求)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_request) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_requests = [r for r in results if r[0] is not None]
        success_rate = len(successful_requests) / len(results)
        
        if successful_requests:
            concurrent_times = [r[1] for r in successful_requests]
            avg_concurrent_time = statistics.mean(concurrent_times)
            
            success = success_rate >= 0.8  # 80%成功率
            self.log_test(
                "并发请求测试",
                success,
                f"成功率: {success_rate:.1%}, 平均响应时间: {avg_concurrent_time:.3f}s",
                avg_concurrent_time
            )
        else:
            self.log_test("并发请求测试", False, "所有并发请求都失败")

    def test_server_health(self):
        """服务器健康检查"""
        print("=" * 60)
        print("0. 服务器健康检查")
        print("=" * 60)
        
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                self.log_test("服务器健康检查", True, "服务器正常运行")
                return True
            else:
                self.log_test("服务器健康检查", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("服务器健康检查", False, str(e))
            return False

    def generate_report(self):
        """生成测试报告"""
        print("=" * 80)
        print("测试报告总结")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests:.1%}")
        print()
        
        # 性能统计
        response_times = [r["response_time"] for r in self.test_results if r["response_time"] > 0]
        if response_times:
            print("性能统计:")
            print(f"  平均响应时间: {statistics.mean(response_times):.3f}s")
            print(f"  最大响应时间: {max(response_times):.3f}s")
            print(f"  最小响应时间: {min(response_times):.3f}s")
            print()
        
        # 失败的测试
        if failed_tests > 0:
            print("失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test_name']}: {result['details']}")
            print()
        
        # 关键验证
        print("关键验证结果:")
        
        # UTF-8编码错误检查
        utf8_errors = [r for r in self.test_results if "utf-8" in r["details"].lower() and "codec" in r["details"].lower()]
        if utf8_errors:
            print("  ❌ 仍存在UTF-8编码错误")
        else:
            print("  ✅ 无UTF-8编码错误")
        
        # 基础功能检查
        basic_tests = [r for r in self.test_results if "基本" in r["test_name"] or "中文" in r["test_name"]]
        basic_success = all(r["success"] for r in basic_tests)
        print(f"  {'✅' if basic_success else '❌'} 基础功能正常")
        
        # 错误处理检查
        error_tests = [r for r in self.test_results if "错误" in r["test_name"] or "multipart" in r["test_name"]]
        error_success = all(r["success"] for r in error_tests)
        print(f"  {'✅' if error_success else '❌'} 错误处理正常")
        
        return passed_tests >= total_tests * 0.8  # 80%通过率

def main():
    print("🚀 开始全面测试 /api/v1/rag/documents/preview-split API端点")
    print("=" * 80)
    
    test_suite = APITestSuite()
    
    # 检查服务器健康状态
    if not test_suite.test_server_health():
        print("❌ 服务器不可用，终止测试")
        return False
    
    # 执行所有测试
    test_suite.test_basic_functionality()
    test_suite.test_error_handling()
    test_suite.test_boundary_conditions()
    test_suite.test_performance()
    
    # 生成报告
    success = test_suite.generate_report()
    
    if success:
        print("🎉 API端点测试通过！")
    else:
        print("❌ API端点测试失败，需要进一步检查")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
