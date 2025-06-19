#!/usr/bin/env python3
"""
直接测试RAG服务功能
"""

import sys
import os
import asyncio
import logging

# 添加项目路径
sys.path.append('.')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_rag_service():
    """测试RAG服务功能"""
    print("=" * 50)
    print("测试RAG服务功能")
    print("=" * 50)
    
    try:
        # 导入RAG组件
        from app.services.rag_service import RAGService
        from app.db.mongodb import mongodb
        
        # 连接数据库
        await mongodb.connect()
        
        # 创建RAG服务实例
        rag_service = RAGService()
        
        # 先检查RAG组件
        print("1. 检查RAG组件初始化...")
        from app.rag import embedding_model, vector_store, retrieval_service
        from app.rag import document_processor, document_splitter

        print(f"嵌入模型: {'✅' if embedding_model is not None else '❌'}")
        print(f"向量存储: {'✅' if vector_store is not None else '❌'}")
        print(f"检索服务: {'✅' if retrieval_service is not None else '❌'}")
        print(f"文档处理器: {'✅' if document_processor is not None else '❌'}")
        print(f"文档分割器: {'✅' if document_splitter is not None else '❌'}")

        # 测试RAG可用性检查
        print("2. 测试RAG可用性检查...")
        is_available = rag_service._check_rag_available()
        print(f"RAG服务可用性: {'✅ 可用' if is_available else '❌ 不可用'}")

        if not is_available:
            print("RAG服务不可用，但继续测试组件...")
            # 不直接返回，继续测试
        
        # 创建测试文件
        test_file_path = "test_simple_upload.txt"
        if not os.path.exists(test_file_path):
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write("这是一个测试文档。\n\n用于测试RAG系统的基本功能。")
        
        print("3. 测试文档处理...")
        result = await rag_service.process_document(
            file_path=test_file_path,
            file_name="test_simple_upload.txt",
            user_id="test_user",
            parent_chunk_size=512,
            child_chunk_size=256
        )
        
        print(f"文档处理结果: {result}")
        
        if result.get("success"):
            print("✅ 文档处理成功")
            doc_id = result.get("doc_id")
            
            # 测试搜索功能
            print("4. 测试搜索功能...")
            search_result = await rag_service.search_documents(
                query="测试",
                user_id="test_user",
                top_k=3
            )
            
            print(f"搜索结果: {search_result}")
            
            if search_result.get("success"):
                print("✅ 搜索功能正常")
                results = search_result.get("results", [])
                print(f"找到 {len(results)} 个相关结果")
            else:
                print("❌ 搜索功能异常")
                
        else:
            print("❌ 文档处理失败")
            print(f"错误信息: {result.get('message')}")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False
    finally:
        # 清理测试文件
        if os.path.exists("test_simple_upload.txt"):
            os.remove("test_simple_upload.txt")

async def main():
    """主函数"""
    print("RAG服务功能测试开始")
    print("=" * 60)
    
    success = await test_rag_service()
    
    print("=" * 60)
    if success:
        print("✅ RAG服务测试完成")
    else:
        print("❌ RAG服务测试失败")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
