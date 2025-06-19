#!/usr/bin/env python3
"""
RAG服务连接诊断脚本
用于诊断Milvus和嵌入模型连接问题
"""

import os
import sys
import requests
import logging
from pymilvus import connections, utility, Collection
import traceback

# 添加项目路径
sys.path.append('.')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_milvus_connection():
    """测试Milvus连接"""
    print("=" * 50)
    print("测试Milvus连接")
    print("=" * 50)
    
    try:
        # 获取配置
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        
        print(f"Milvus配置: {milvus_host}:{milvus_port}")
        
        # 尝试连接 - 使用Docker中的Milvus连接方式
        connections.connect(host=milvus_host, port=str(milvus_port))
        print("✅ Milvus连接成功")

        # 列出集合
        collections = utility.list_collections()
        print(f"现有集合: {collections}")

        # 断开连接
        connections.disconnect("default")
        return True
        
    except Exception as e:
        print(f"❌ Milvus连接失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")
        return False

def test_embedding_api():
    """测试嵌入模型API连接"""
    print("=" * 50)
    print("测试嵌入模型API连接")
    print("=" * 50)
    
    try:
        # 获取配置
        api_base = os.getenv("EMBEDDING_API_BASE", "http://192.168.1.30:1234")
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
        
        print(f"API地址: {api_base}")
        print(f"模型名称: {model_name}")
        
        # 测试OpenAI兼容API
        print("\n测试OpenAI兼容API (/v1/embeddings)...")
        response = requests.post(
            f"{api_base}/v1/embeddings",
            json={
                "model": model_name,
                "input": "测试文本"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "data" in result and len(result["data"]) > 0:
                embedding = result["data"][0]["embedding"]
                print(f"✅ OpenAI兼容API调用成功")
                print(f"向量维度: {len(embedding)}")
                print(f"前5个值: {embedding[:5]}")
                return True, len(embedding)
            else:
                print(f"❌ API响应格式错误: {result}")
                return False, None
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            # 尝试Ollama风格API
            print("\n测试Ollama风格API (/api/embeddings)...")
            response2 = requests.post(
                f"{api_base}/api/embeddings",
                json={
                    "model": model_name,
                    "prompt": "测试文本"
                },
                timeout=10
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"✅ Ollama风格API调用成功")
                print(f"响应: {result2}")
                return True, None
            else:
                print(f"❌ Ollama风格API也失败: {response2.status_code}")
                print(f"响应内容: {response2.text}")
                return False, None
                
    except Exception as e:
        print(f"❌ 嵌入模型API测试失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")
        return False, None

def test_rag_components():
    """测试RAG组件初始化"""
    print("=" * 50)
    print("测试RAG组件初始化")
    print("=" * 50)
    
    try:
        from app.rag import embedding_model, vector_store, retrieval_service
        
        print(f"嵌入模型: {'✅ 已初始化' if embedding_model is not None else '❌ 未初始化'}")
        print(f"向量存储: {'✅ 已初始化' if vector_store is not None else '❌ 未初始化'}")
        print(f"检索服务: {'✅ 已初始化' if retrieval_service is not None else '❌ 未初始化'}")
        
        if embedding_model:
            print(f"嵌入模型配置: {embedding_model.model_name} @ {embedding_model.api_base}")
            
            # 测试get_dimension方法
            try:
                print("测试get_dimension方法...")
                dimension = embedding_model.get_dimension()
                print(f"✅ 获取向量维度成功: {dimension}")
            except Exception as e:
                print(f"❌ 获取向量维度失败: {str(e)}")
                
        if vector_store:
            print(f"向量存储配置: {vector_store.host}:{vector_store.port}")
            
        return True
        
    except Exception as e:
        print(f"❌ RAG组件初始化失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    print("RAG服务连接诊断开始")
    print("=" * 60)
    
    # 显示环境变量
    print("环境变量:")
    print(f"MILVUS_HOST: {os.getenv('MILVUS_HOST', 'localhost')}")
    print(f"MILVUS_PORT: {os.getenv('MILVUS_PORT', '19530')}")
    print(f"EMBEDDING_MODEL: {os.getenv('EMBEDDING_MODEL', 'text-embedding-nomic-embed-text-v1.5')}")
    print(f"EMBEDDING_API_BASE: {os.getenv('EMBEDDING_API_BASE', 'http://192.168.1.30:1234')}")
    print()
    
    # 测试各个组件
    milvus_ok = test_milvus_connection()
    embedding_ok, dimension = test_embedding_api()
    rag_ok = test_rag_components()
    
    # 总结
    print("=" * 60)
    print("诊断总结:")
    print(f"Milvus连接: {'✅ 正常' if milvus_ok else '❌ 异常'}")
    print(f"嵌入模型API: {'✅ 正常' if embedding_ok else '❌ 异常'}")
    print(f"RAG组件: {'✅ 正常' if rag_ok else '❌ 异常'}")
    
    if dimension:
        print(f"向量维度: {dimension}")
    
    if not all([milvus_ok, embedding_ok, rag_ok]):
        print("\n❌ 发现问题，请检查上述错误信息")
        return 1
    else:
        print("\n✅ 所有组件正常")
        return 0

if __name__ == "__main__":
    sys.exit(main())
