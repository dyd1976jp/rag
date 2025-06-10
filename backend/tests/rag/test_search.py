#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试RAG文档搜索功能
"""

import os
import sys
import logging
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.rag import vector_store, embedding_model, retrieval_service
from app.services.rag_service import RAGService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search():
    """测试搜索功能"""
    print("RAG搜索测试:")
    print("-" * 50)
    
    # 检查各组件状态
    print(f"向量存储可用: {vector_store is not None}")
    print(f"嵌入模型可用: {embedding_model is not None}")
    print(f"检索服务可用: {retrieval_service is not None}")
    
    if not all([vector_store, embedding_model, retrieval_service]):
        print("错误: 某些RAG组件不可用，无法测试搜索功能")
        return
    
    try:
        # 测试集合状态
        collection_name = "rag_documents"
        print(f"\n集合 {collection_name} 状态检查:")
        
        # 确保集合正确初始化
        vector_store.collection = None
        vector_store.create_collection(collection_name)
        print(f"集合是否正确加载: {vector_store.collection is not None}")
        
        if vector_store.collection:
            print(f"集合实体数量: {vector_store.collection.num_entities}")
        
        # 测试嵌入模型
        print("\n嵌入模型测试:")
        query = "测试查询内容"
        query_vector = embedding_model.embed_query(query)
        print(f"查询向量维度: {len(query_vector)}")
        
        # 直接使用向量存储进行搜索
        print("\n向量存储直接搜索测试:")
        try:
            results = vector_store.search_by_vector(query_vector, top_k=3)
            print(f"搜索结果数量: {len(results)}")
            for i, doc in enumerate(results):
                print(f"结果 {i+1}:")
                print(f"  内容: {doc.page_content[:100]}...")
                print(f"  元数据: {doc.metadata}")
        except Exception as e:
            print(f"向量存储搜索失败: {e}")
        
        # 使用检索服务进行搜索
        print("\n检索服务搜索测试:")
        try:
            results = retrieval_service.retrieve(query, top_k=3)
            print(f"搜索结果数量: {len(results)}")
            for i, doc in enumerate(results):
                print(f"结果 {i+1}:")
                print(f"  内容: {doc.page_content[:100]}...")
                print(f"  元数据: {doc.metadata}")
        except Exception as e:
            print(f"检索服务搜索失败: {e}")
        
        # 使用RAG服务进行搜索
        print("\nRAG服务搜索测试:")
        try:
            rag_service = RAGService()
            search_result = await rag_service.search_documents(query, user_id="test_user", top_k=3)
            print(f"搜索结果: {search_result}")
        except Exception as e:
            print(f"RAG服务搜索失败: {e}")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search()) 