#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接测试LM Studio API
"""

import requests
import json

# LM Studio API URL
LM_STUDIO_URL = "http://0.0.0.0:1234"

def pretty_print_json(data):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    # 直接测试LM Studio API
    print("\n=== 直接测试LM Studio API ===")
    models_url = f"{LM_STUDIO_URL}/v1/models/"
    
    print(f"请求URL: {models_url}")
    
    try:
        response = requests.get(models_url, timeout=5)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("获取模型列表成功!")
            data = response.json()
            models = data.get('data', [])
            print(f"模型数量: {len(models)}")
            pretty_print_json(data)
            
            # 过滤掉embedding模型，选择适当的LLM模型
            llm_models = [model for model in models if not "embed" in model.get('id', '').lower()]
            if llm_models:
                selected_model = llm_models[0]
                model_id = selected_model.get('id')
                print(f"\n=== 选择LLM模型: {model_id} ===")
                
                # 构建一个简单请求以测试该模型
                chat_url = f"{LM_STUDIO_URL}/v1/chat/completions"
                chat_data = {
                    "messages": [
                        {"role": "user", "content": "Hello, what can you do?"}
                    ],
                    "model": model_id,
                    "max_tokens": 100
                }
                
                print(f"尝试使用模型 {model_id} 发送简单消息")
                try:
                    chat_response = requests.post(chat_url, json=chat_data, timeout=10)
                    print(f"聊天响应状态码: {chat_response.status_code}")
                    
                    if chat_response.status_code == 200:
                        chat_result = chat_response.json()
                        print("聊天响应成功:")
                        pretty_print_json(chat_result)
                    else:
                        print(f"聊天请求失败: {chat_response.status_code}")
                        print(f"错误信息: {chat_response.text}")
                except Exception as chat_error:
                    print(f"聊天请求时出错: {str(chat_error)}")
            else:
                print("未找到合适的LLM模型，仅发现嵌入式模型")
        else:
            print(f"获取模型列表失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"请求模型列表时出错: {str(e)}")

if __name__ == "__main__":
    main() 