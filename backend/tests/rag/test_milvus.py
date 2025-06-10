#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试Milvus集合
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.rag import vector_store
from pymilvus import utility

def check_milvus_collections():
    """检查Milvus集合"""
    print("Milvus集合检查:")
    print("-" * 50)
    
    # 先清除集合对象
    vector_store.collection = None
    
    # 检查集合是否存在
    collection_name = "rag_documents"
    exists = utility.has_collection(collection_name, using="default")
    print(f"集合 {collection_name} 是否存在: {exists}")
    
    if exists:
        # 检查集合的加载状态
        load_state = utility.load_state(collection_name, using="default")
        print(f"集合加载状态: {load_state}")
        
        try:
            # 尝试加载集合
            print("尝试创建/加载集合...")
            vector_store.create_collection(collection_name)
            print("集合创建/加载成功")
            
            # 获取集合实体数量
            if vector_store.collection:
                print(f"集合实体数量: {vector_store.collection.num_entities}")
            else:
                print("警告: 集合对象未初始化")
                
        except Exception as e:
            print(f"集合操作失败: {e}")
    else:
        print("集合不存在，尝试创建...")
        try:
            vector_store.create_collection(collection_name)
            print("集合创建成功")
            # 获取集合实体数量
            if vector_store.collection:
                print(f"集合实体数量: {vector_store.collection.num_entities}")
            else:
                print("警告: 集合对象未初始化")
        except Exception as e:
            print(f"创建集合失败: {e}")
    
    print("\n检查所有集合:")
    try:
        all_collections = utility.list_collections()
        print(f"所有集合: {all_collections}")
    except Exception as e:
        print(f"获取集合列表失败: {e}")

if __name__ == "__main__":
    check_milvus_collections() 