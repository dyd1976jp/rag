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

        # 尝试多种连接方式
        connection_methods = [
            # 方法1: 基本连接
            lambda: connections.connect(host=milvus_host, port=milvus_port),
            # 方法2: 字符串端口
            lambda: connections.connect(host=milvus_host, port=str(milvus_port)),
            # 方法3: 指定别名
            lambda: connections.connect("default", host=milvus_host, port=milvus_port),
            # 方法4: 使用URI
            lambda: connections.connect(uri=f"http://{milvus_host}:{milvus_port}"),
        ]

        for i, method in enumerate(connection_methods, 1):
            try:
                print(f"尝试连接方法 {i}...")
                method()
                print("✅ Milvus连接成功")

                # 列出集合
                collections = utility.list_collections()
                print(f"现有集合: {collections}")

                # 断开连接
                connections.disconnect("default")
                return True

            except Exception as method_error:
                print(f"方法 {i} 失败: {str(method_error)}")
                try:
                    connections.disconnect("default")
                except:
                    pass
                continue

        print("❌ 所有连接方法都失败了")
        return False

    except Exception as e:
        print(f"❌ Milvus连接测试异常: {str(e)}")
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

def fix_milvus_index():
    """修复Milvus集合索引问题"""
    print("=" * 50)
    print("修复Milvus集合索引")
    print("=" * 50)

    try:
        from pymilvus import Collection, utility

        # 获取配置
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        collection_name = "rag_documents"

        print(f"连接到Milvus: {milvus_host}:{milvus_port}")
        connections.connect(host=milvus_host, port=str(milvus_port))

        # 检查集合是否存在
        if not utility.has_collection(collection_name):
            print(f"❌ 集合 {collection_name} 不存在")
            return False

        collection = Collection(collection_name)
        print(f"✅ 找到集合 {collection_name}")

        # 检查集合schema
        schema = collection.schema
        print(f"集合字段: {[field.name for field in schema.fields]}")

        # 检查索引
        indexes = collection.indexes
        print(f"当前索引: {[idx.field_name for idx in indexes]}")

        # 检查向量字段是否有索引
        vector_field = "vector"
        has_vector_index = any(idx.field_name == vector_field for idx in indexes)

        if not has_vector_index:
            print(f"❌ 向量字段 '{vector_field}' 没有索引，正在创建...")

            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
                "metric_type": "L2"
            }

            collection.create_index(field_name=vector_field, index_params=index_params)
            print(f"✅ 为字段 '{vector_field}' 创建索引成功")

            # 等待索引构建完成
            utility.wait_for_index_building_complete(collection_name, vector_field)
            print(f"✅ 索引构建完成")
        else:
            print(f"✅ 向量字段 '{vector_field}' 已有索引")

        # 断开连接
        connections.disconnect("default")
        return True

    except Exception as e:
        print(f"❌ 修复索引失败: {str(e)}")
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

    # 修复Milvus索引问题
    if milvus_ok:
        index_ok = fix_milvus_index()
    else:
        index_ok = False

    # 总结
    print("=" * 60)
    print("诊断总结:")
    print(f"Milvus连接: {'✅ 正常' if milvus_ok else '❌ 异常'}")
    print(f"嵌入模型API: {'✅ 正常' if embedding_ok else '❌ 异常'}")
    print(f"RAG组件: {'✅ 正常' if rag_ok else '❌ 异常'}")
    print(f"Milvus索引: {'✅ 正常' if index_ok else '❌ 异常'}")

    if dimension:
        print(f"向量维度: {dimension}")

    if not all([milvus_ok, embedding_ok, rag_ok, index_ok]):
        print("\n❌ 发现问题，请检查上述错误信息")
        return 1
    else:
        print("\n✅ 所有组件正常")
        return 0

if __name__ == "__main__":
    sys.exit(main())
