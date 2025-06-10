#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试查看Milvus中的dataset_id
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.rag import vector_store

def check_dataset_ids():
    """检查Milvus中的dataset_id"""
    print("Milvus数据集ID检查:")
    print("-" * 50)
    
    collection_name = "rag_documents"
    
    try:
        # 确保集合加载
        vector_store.collection = None
        vector_store.create_collection(collection_name)
        
        if not vector_store.collection:
            print(f"错误: 集合 {collection_name} 加载失败")
            return
        
        # 查询所有文档的dataset_id
        print(f"正在查询集合 {collection_name} 中的dataset_id...")
        
        # 使用query获取所有文档的dataset_id
        results = vector_store.collection.query(
            expr="id != ''", 
            output_fields=["id", "metadata"],
            limit=10
        )
        
        if not results:
            print("未找到任何数据")
            return
        
        # 提取唯一的dataset_id
        dataset_ids = set()
        for item in results:
            metadata = item.get("metadata", {})
            dataset_id = metadata.get("dataset_id")
            if dataset_id:
                dataset_ids.add(dataset_id)
        
        print(f"找到 {len(dataset_ids)} 个不同的dataset_id:")
        for dataset_id in dataset_ids:
            print(f"  - {dataset_id}")
            
        # 统计每个dataset_id的文档数量
        print("\n每个dataset_id的文档数量:")
        for dataset_id in dataset_ids:
            count_expr = f'metadata["dataset_id"] == "{dataset_id}"'
            count_results = vector_store.collection.query(
                expr=count_expr,
                output_fields=["id"],
                limit=1000
            )
            print(f"  - {dataset_id}: {len(count_results)} 个文档")
        
    except Exception as e:
        print(f"查询dataset_id失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_dataset_ids() 