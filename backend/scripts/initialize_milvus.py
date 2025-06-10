"""
初始化 Milvus 集合的脚本
"""

import os
import sys
from app.rag import vector_store, embedding_model

def main():
    """主函数"""
    print("==================================================")
    print("Milvus 集合初始化和验证")
    print("==================================================")
    
    # 步骤1: 检查向量存储连接
    print("\n步骤1: 检查向量存储连接")
    print(f"向量存储连接: {vector_store.host}:{vector_store.port}")
    
    # 步骤2: 创建/加载集合
    print("\n步骤2: 创建/加载集合")
    dimension = embedding_model.get_dimension()
    print(f"嵌入向量维度: {dimension}")
    
    collection_name = os.environ.get("MILVUS_COLLECTION", "rag_documents")
    print(f"正在创建/加载集合: {collection_name}")
    vector_store.create_collection(collection_name, dimension)
    
    # 步骤3: 验证集合索引
    print("\n步骤3: 验证集合索引")
    try:
        stats = vector_store.get_stats()
        print(f"集合统计信息:")
        print(f"- 集合名称: {stats['collection_name']}")
        print(f"- 实体数量: {stats['row_count']}")
        print(f"- 索引信息: {stats['index_info']}")
        print(f"- 字段信息: {stats['schema']}")
    except Exception as e:
        print(f"获取索引信息时出错: {e}")

if __name__ == "__main__":
    main() 