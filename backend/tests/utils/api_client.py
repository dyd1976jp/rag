#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM API 测试脚本

测试LLM API的各个端点，包括：
- 获取所有模型
- 发现LM Studio中的模型
- 注册模型
- 测试模型
"""

import requests
import json
import time
import os
import sys
from typing import Dict, Any, List, Optional

# 配置
API_URL = "http://localhost:8000"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzQ4MjYyNzUwfQ.x9vEcvY7OsoTVMmQTL8I4cqV2Cm8RjLqi61jI4lYZEg"
LM_STUDIO_URL = "http://0.0.0.0:1234"  # LM Studio API URL

# 颜色定义
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def log_info(message: str) -> None:
    """输出信息日志"""
    print(f"{Colors.BLUE}[信息]{Colors.ENDC} {message}")

def log_success(message: str) -> None:
    """输出成功日志"""
    print(f"{Colors.GREEN}[成功]{Colors.ENDC} {message}")

def log_error(message: str) -> None:
    """输出错误日志"""
    print(f"{Colors.RED}[错误]{Colors.ENDC} {message}")

def log_title(message: str) -> None:
    """输出标题"""
    print(f"\n{Colors.YELLOW}=== {message} ==={Colors.ENDC}")

def pretty_print_json(data: Dict[str, Any]) -> None:
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

class LLMApiTester:
    """LLM API测试类"""
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        self.discovered_models = []
        self.registered_model_id = None
    
    def test_get_all_llms(self) -> bool:
        """测试获取所有LLM模型"""
        log_title("测试获取所有LLM模型")
        
        # 尝试不同的API路径
        api_paths = [
            f"{API_URL}/api/v1/llm/",
            f"{API_URL}/api/llm/"
        ]
        
        for path in api_paths:
            log_info(f"尝试API路径: {path}")
            # 打印 curl 命令
            curl_cmd = f"curl -X GET '{path}' -H 'Authorization: Bearer {AUTH_TOKEN}' -H 'Content-Type: application/json'"
            log_info(f"curl 命令: {curl_cmd}")
            response = requests.get(
                path,
                headers=self.headers
            )
            
            if response.status_code == 200:
                models = response.json()
                log_success(f"API路径 {path} 成功!")
                log_success(f"获取到 {len(models)} 个LLM模型")
                pretty_print_json(models)
                return True
            else:
                log_error(f"API路径 {path} 失败: {response.status_code}")
                try:
                    error_detail = response.json().get("detail", "未知错误")
                    log_error(f"错误详情: {error_detail}")
                except:
                    log_error(f"无法解析错误: {response.text}")
        
        # 如果所有路径都失败
        log_error("所有API路径尝试都失败了")
        return False
    
    def test_discover_models(self) -> bool:
        """测试发现LM Studio中的模型"""
        log_title("测试发现LM Studio中的模型")
        
        # 先测试LM Studio是否可以访问
        log_info("尝试直接访问LM Studio API...")
        try:
            lm_studio_response = requests.get(f"{LM_STUDIO_URL}/v1/models/", timeout=5)
            if lm_studio_response.status_code == 200:
                log_success("LM Studio API 可以访问")
                log_info(f"可用模型: {len(lm_studio_response.json().get('data', []))}")
            else:
                log_error(f"LM Studio API返回错误: {lm_studio_response.status_code}")
        except Exception as e:
            log_error(f"无法连接到LM Studio: {str(e)}")
        
        # 尝试不同的API路径
        api_paths = [
            f"{API_URL}/api/v1/llm/discover",
            f"{API_URL}/api/llm/discover"
        ]
        
        for path in api_paths:
            log_info(f"尝试API路径: {path}")
            # 打印 curl 命令
            curl_cmd = f"curl -X GET '{path}?provider=lmstudio&url={LM_STUDIO_URL}' -H 'Authorization: Bearer {AUTH_TOKEN}' -H 'Content-Type: application/json'"
            log_info(f"curl 命令: {curl_cmd}")
            response = requests.get(
                path,
                params={"provider": "lmstudio", "url": LM_STUDIO_URL},
                headers=self.headers
            )
            
            if response.status_code == 200:
                self.discovered_models = response.json()
                log_success(f"API路径 {path} 成功!")
                log_success(f"发现了 {len(self.discovered_models)} 个模型")
                pretty_print_json(self.discovered_models)
                return True
            else:
                log_error(f"API路径 {path} 失败: {response.status_code}")
                try:
                    error_detail = response.json().get("detail", "未知错误")
                    log_error(f"错误详情: {error_detail}")
                except:
                    log_error(f"无法解析错误: {response.text}")
        
        # 如果所有路径都失败
        log_error("所有API路径尝试都失败了")
        
        # 诊断信息
        log_info("\n诊断信息:")
        log_info(f"- API URL: {API_URL}")
        log_info(f"- LM Studio URL: {LM_STUDIO_URL}")
        log_info(f"- 授权令牌: {AUTH_TOKEN[:10]}...")
        
        return False
    
    def test_register_model(self) -> bool:
        """测试注册模型"""
        log_title("测试注册模型")
        
        if not self.discovered_models:
            log_error("没有可用的模型，请先运行发现模型的测试")
            return False
        
        first_model = self.discovered_models[0]
        model_id = first_model.get("id")
        model_name = first_model.get("name")
        api_url = first_model.get("api_url")
        
        log_info(f"准备注册模型: {model_id}")
        
        data = {
            "llm_model_id": model_id,
            "provider": "Local",
            "name": f"测试自动注册 - {model_name}",
            "api_url": api_url,
            "description": "通过Python测试脚本自动注册的模型",
            "context_window": 8192,
            "set_as_default": True
        }
        
        # 尝试不同的API路径
        api_paths = [
            f"{API_URL}/api/v1/llm/register-from-discovery",
            f"{API_URL}/api/llm/register-from-discovery"
        ]
        
        for path in api_paths:
            log_info(f"尝试API路径: {path}")
            response = requests.post(
                path,
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 201:
                result = response.json()
                self.registered_model_id = result.get("id")
                log_success(f"API路径 {path} 成功!")
                log_success(f"模型注册成功，ID: {self.registered_model_id}")
                pretty_print_json(result)
                return True
            else:
                log_error(f"API路径 {path} 失败: {response.status_code}")
                try:
                    error_detail = response.json().get("detail", "未知错误")
                    log_error(f"错误详情: {error_detail}")
                except:
                    log_error(f"无法解析错误: {response.text}")
        
        # 如果所有路径都失败
        log_error("所有API路径尝试都失败了")
        return False
    
    def test_model(self) -> bool:
        """测试模型运行"""
        log_title("测试模型运行")
        
        if not self.registered_model_id:
            log_error("没有注册的模型ID，请先运行注册模型的测试")
            return False
        
        log_info(f"测试模型: {self.registered_model_id}")
        
        data = {
            "llm_id": self.registered_model_id,
            "prompt": "你好，请用中文简单介绍一下你自己。"
        }
        
        response = requests.post(
            f"{API_URL}/api/v1/llm/test",
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            log_success("模型测试成功")
            pretty_print_json(result)
            return True
        else:
            log_error(f"测试模型失败: {response.status_code}")
            try:
                log_error(response.json().get("detail", "未知错误"))
            except:
                log_error(f"无法解析错误: {response.text}")
            return False
    
    def run_all_tests(self) -> None:
        """运行所有测试"""
        tests = [
            self.test_get_all_llms,
            self.test_discover_models,
            self.test_register_model,
            self.test_model
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
            if not result:
                log_error(f"测试 {test.__name__} 失败，终止后续测试")
                break
            time.sleep(1)  # 添加短暂延迟，避免API请求过快
        
        log_title("测试结果汇总")
        for i, test in enumerate(tests):
            if i < len(results):
                status = f"{Colors.GREEN}通过{Colors.ENDC}" if results[i] else f"{Colors.RED}失败{Colors.ENDC}"
                print(f"- {test.__name__}: {status}")
            else:
                print(f"- {test.__name__}: {Colors.YELLOW}未运行{Colors.ENDC}")
        
        total = len(results)
        passed = sum(1 for r in results if r)
        print(f"\n总测试数: {total}, 通过: {passed}, 失败: {total - passed}")

def main():
    """主函数"""
    log_title("LLM API 测试脚本")
    tester = LLMApiTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 