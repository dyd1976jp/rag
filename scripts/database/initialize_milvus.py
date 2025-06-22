#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Milvus 集合初始化和验证脚本
"""

import os
import sys
import logging

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.rag import vector_store, embedding_model

def initialize_milvus_collection():
    """初始化并验证 Milvus 集合"""
    print("=" * 50)
    print("Milvus 集合初始化和验证")
    print("=" * 50)
    
    # 步骤1: 确保向量存储连接正常
    print("\n步骤1: 检查向量存储连接")
    if vector_store is None:
        print("错误: 向量存储未初始化")
        return False
    
    print(f"向量存储连接: {vector_store.host}:{vector_store.port}")
    
    # 步骤2: 创建/加载集合
    print("\n步骤2: 创建/加载集合")
    try:
        # 清除当前集合引用
        vector_store.collection = None
        
        # 获取嵌入维度
        dimension = embedding_model.get_dimension()
        print(f"嵌入向量维度: {dimension}")
        
        # 创建或加载集合
        collection_name = os.environ.get("MILVUS_COLLECTION", "rag_documents")
        print(f"正在创建/加载集合: {collection_name}")
        vector_store.create_collection(collection_name, dimension)
        
        if vector_store.collection:
            print(f"集合 {collection_name} 创建/加载成功")
            print(f"集合实体数量: {vector_store.collection.num_entities}")
        else:
            print(f"错误: 集合 {collection_name} 创建/加载失败")
            return False
    except Exception as e:
        print(f"创建/加载集合时出错: {e}")
        return False
    
    # 步骤3: 验证集合索引和统计信息
    print("\n步骤3: 验证集合索引和统计信息")
    try:
        stats = vector_store.get_stats()
        print(f"集合统计信息:")
        print(f"- 集合名称: {stats['collection_name']}")
        print(f"- 实体数量: {stats['row_count']}")
        print(f"- 索引信息: {stats['index_info']}")
        print(f"- 字段信息: {stats['schema']}")
    except Exception as e:
        print(f"获取索引信息时出错: {e}")
        return False
    
    # 步骤4: 执行简单搜索测试
    print("\n步骤4: 执行搜索测试")
    try:
        # 生成测试向量
        test_vector = [0.0] * dimension
        
        # 执行搜索
        print("执行测试搜索...")
        results = vector_store.search_by_vector(test_vector, top_k=1)
        
        if results:
            print(f"搜索成功，找到 {len(results)} 个结果")
        else:
            print("搜索成功，但没有找到匹配结果（这是正常的，如果集合中没有数据）")
    except Exception as e:
        print(f"搜索测试失败: {e}")
        return False
    
    print("\n初始化和验证完成！")
    print("Milvus 集合已经准备就绪，可以使用了。")
    return True

if __name__ == "__main__":
    initialize_milvus_collection() 