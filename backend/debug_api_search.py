#!/usr/bin/env python3
"""
调试API搜索问题的脚本
"""
import os
import sys
import asyncio
import json
sys.path.append('.')

from app.services.rag_service import rag_service

async def debug_api_search():
    """调试API搜索问题"""
    print("=== API搜索问题调试 ===\n")

    # 首先初始化MongoDB和RAG组件
    print("0. 初始化系统组件...")
    from app.db.mongodb import mongodb
    await mongodb.connect()
    print("MongoDB连接成功")

    from app.rag import initialize_rag
    await initialize_rag()
    print("RAG组件初始化完成")

    # 测试用户ID（从你的JWT token中提取）
    test_user_id = "test2@example.com"  # 根据JWT token中的sub字段

    # 测试查询
    test_query = "这个文档将用于测试父子分割功能。"

    print(f"测试用户ID: {test_user_id}")
    print(f"测试查询: {test_query}")
    print()
    
    # 1. 测试RAG服务可用性
    print("1. 检查RAG服务可用性...")
    try:
        is_available = rag_service._check_rag_available()
        print(f"✓ RAG服务可用性: {is_available}")
        
        if not is_available:
            print("✗ RAG服务不可用，无法继续测试")
            return
    except Exception as e:
        print(f"✗ 检查RAG服务可用性失败: {e}")
        return
    
    # 2. 测试标准搜索（不包含父文档）
    print("\n2. 测试标准搜索（不包含父文档）...")
    try:
        result = await rag_service.search_documents(
            query=test_query,
            user_id=test_user_id,
            top_k=5,
            search_all=True,  # 搜索所有用户的文档
            include_parent=False
        )
        
        print(f"搜索结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result["success"]:
            print(f"✓ 标准搜索成功，找到 {len(result['results'])} 个结果")
        else:
            print(f"✗ 标准搜索失败: {result['message']}")
            
    except Exception as e:
        print(f"✗ 标准搜索异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. 测试父子文档搜索
    print("\n3. 测试父子文档搜索...")
    try:
        result = await rag_service.search_documents(
            query=test_query,
            user_id=test_user_id,
            top_k=5,
            search_all=True,  # 搜索所有用户的文档
            include_parent=True
        )
        
        print(f"搜索结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result["success"]:
            print(f"✓ 父子文档搜索成功，找到 {len(result['results'])} 个结果")
        else:
            print(f"✗ 父子文档搜索失败: {result['message']}")
            
    except Exception as e:
        print(f"✗ 父子文档搜索异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. 测试限制用户搜索
    print("\n4. 测试限制用户搜索...")
    try:
        result = await rag_service.search_documents(
            query=test_query,
            user_id=test_user_id,
            top_k=5,
            search_all=False,  # 只搜索当前用户的文档
            include_parent=True
        )
        
        print(f"搜索结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result["success"]:
            print(f"✓ 限制用户搜索成功，找到 {len(result['results'])} 个结果")
        else:
            print(f"✗ 限制用户搜索失败: {result['message']}")
            
    except Exception as e:
        print(f"✗ 限制用户搜索异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 直接测试检索服务
    print("\n5. 直接测试检索服务...")
    try:
        components = rag_service._get_rag_components()
        retrieval_service = components['retrieval_service']
        
        # 测试标准检索
        print("  5.1 测试标准检索...")
        results = retrieval_service.retrieve(
            query=test_query,
            dataset_id=None,  # 不限制数据集
            top_k=5,
            use_cache=False
        )
        
        print(f"  标准检索结果数量: {len(results)}")
        for i, doc in enumerate(results):
            print(f"    结果 {i+1}: {doc.page_content[:50]}... (score: {doc.metadata.get('score', 'N/A')})")
        
        # 测试父子检索
        print("\n  5.2 测试父子检索...")
        parent_results = retrieval_service.retrieve_with_parent(
            query=test_query,
            dataset_id=None,  # 不限制数据集
            top_k=5,
            use_cache=False
        )
        
        print(f"  父子检索结果数量: {len(parent_results)}")
        for i, result in enumerate(parent_results):
            child_doc = result.get("child_document")
            parent_doc = result.get("parent_document")
            score = result.get("score", 0.0)
            
            print(f"    结果 {i+1}:")
            print(f"      子文档: {child_doc.page_content[:50] if child_doc else 'None'}...")
            print(f"      父文档: {parent_doc.page_content[:50] if parent_doc else 'None'}...")
            print(f"      分数: {score}")
        
    except Exception as e:
        print(f"✗ 直接测试检索服务异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    asyncio.run(debug_api_search())
