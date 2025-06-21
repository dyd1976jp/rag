#!/usr/bin/env python3
"""
调试RAG搜索问题的脚本
"""
import os
import sys
import numpy as np
sys.path.append('.')

from pymilvus import connections, Collection, utility
from app.rag.embedding_model import EmbeddingModel

def debug_search_issue():
    """调试搜索问题"""
    print("=== RAG搜索问题调试 ===\n")
    
    # 1. 连接Milvus
    print("1. 连接Milvus...")
    try:
        connections.connect(host='localhost', port='19530')
        print("✓ Milvus连接成功")
    except Exception as e:
        print(f"✗ Milvus连接失败: {e}")
        return
    
    # 2. 检查集合
    print("\n2. 检查集合...")
    collection_name = 'rag_documents'
    if not utility.has_collection(collection_name):
        print(f"✗ 集合 {collection_name} 不存在")
        return
    
    collection = Collection(collection_name)
    collection.load()
    print(f"✓ 集合 {collection_name} 存在，实体数量: {collection.num_entities}")
    
    # 3. 测试嵌入模型
    print("\n3. 测试嵌入模型...")
    try:
        embedding_model = EmbeddingModel()
        test_query = '这个文档将用于测试父子分割功能。'
        query_vector = embedding_model.embed_query(test_query)
        print(f"✓ 查询向量生成成功，维度: {len(query_vector)}")
        print(f"  向量前5个值: {query_vector[:5]}")
    except Exception as e:
        print(f"✗ 嵌入模型测试失败: {e}")
        return
    
    # 4. 查找包含特定文本的记录
    print("\n4. 查找包含特定文本的记录...")
    try:
        all_records = collection.query(
            expr='',
            limit=50,
            output_fields=['id', 'page_content', 'metadata']
        )
        
        target_text = '这个文档将用于测试父子分割功能'
        matching_records = []
        
        for record in all_records:
            content = record.get('page_content', '')
            if target_text in content:
                matching_records.append(record)
        
        print(f"✓ 找到 {len(matching_records)} 条包含目标文本的记录")
        
        if matching_records:
            for i, record in enumerate(matching_records):
                print(f"\n  记录 {i+1}:")
                print(f"    ID: {record['id']}")
                print(f"    内容: {record['page_content'][:100]}...")
                print(f"    元数据: {record['metadata']}")
                
                # 计算这条记录与查询的相似度
                try:
                    record_vector = embedding_model.embed_query(record['page_content'])
                    
                    # 计算余弦相似度
                    def cosine_similarity(a, b):
                        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
                    
                    similarity = cosine_similarity(query_vector, record_vector)
                    l2_distance = np.linalg.norm(np.array(query_vector) - np.array(record_vector))
                    
                    print(f"    余弦相似度: {similarity:.4f}")
                    print(f"    L2距离: {l2_distance:.4f}")
                except Exception as e:
                    print(f"    相似度计算失败: {e}")
        
    except Exception as e:
        print(f"✗ 查找记录失败: {e}")
        return
    
    # 5. 执行向量搜索
    print("\n5. 执行向量搜索...")
    try:
        search_params = {
            'metric_type': 'L2',
            'params': {'nprobe': 10}
        }
        
        search_results = collection.search(
            data=[query_vector],
            anns_field='vector',
            param=search_params,
            limit=10,
            output_fields=['page_content', 'metadata']
        )
        
        print(f"✓ 搜索执行成功，结果数量: {len(search_results[0]) if search_results else 0}")
        
        if search_results and len(search_results[0]) > 0:
            print("\n  搜索结果:")
            for i, hit in enumerate(search_results[0]):
                print(f"    结果 {i+1}:")
                print(f"      距离: {hit.distance:.4f}")
                content = hit.entity.get('page_content', 'N/A')
                print(f"      内容: {content[:100]}...")
                print(f"      元数据: {hit.entity.get('metadata', {})}")
                
                # 检查是否包含目标文本
                if target_text in content:
                    print(f"      *** 包含目标文本! ***")
                print()
        else:
            print("  没有找到搜索结果")
            
    except Exception as e:
        print(f"✗ 向量搜索失败: {e}")
        return
    
    # 6. 测试不同的搜索参数
    print("\n6. 测试不同的搜索参数...")
    test_params = [
        {'metric_type': 'L2', 'params': {'nprobe': 50}},
        {'metric_type': 'IP', 'params': {'nprobe': 10}},
        {'metric_type': 'COSINE', 'params': {'nprobe': 10}},
    ]
    
    for params in test_params:
        try:
            results = collection.search(
                data=[query_vector],
                anns_field='vector',
                param=params,
                limit=5,
                output_fields=['page_content']
            )
            
            result_count = len(results[0]) if results else 0
            print(f"  {params['metric_type']}: {result_count} 个结果")
            
            if results and len(results[0]) > 0:
                for hit in results[0]:
                    content = hit.entity.get('page_content', '')
                    if target_text in content:
                        print(f"    *** 找到目标文本! 距离: {hit.distance:.4f} ***")
                        break
                        
        except Exception as e:
            print(f"  {params['metric_type']}: 搜索失败 - {e}")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_search_issue()
