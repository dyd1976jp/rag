#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试RAG服务状态
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.rag import vector_store, embedding_model, retrieval_service
from app.rag import document_processor, document_splitter, pdf_processor

def check_rag_status():
    """检查RAG服务状态"""
    print("RAG服务状态检查:")
    print("-" * 50)
    
    # 检查各组件状态
    status = {
        "vector_store_available": vector_store is not None,
        "embedding_model_available": embedding_model is not None,
        "retrieval_service_available": retrieval_service is not None,
        "document_processor_available": document_processor is not None,
        "document_splitter_available": document_splitter is not None,
        "pdf_processor_available": pdf_processor is not None
    }
    
    # 打印各组件状态
    for component, available in status.items():
        print(f"{component}: {'可用' if available else '不可用'}")
    
    # 整体可用性判断
    rag_available = status["vector_store_available"] and status["embedding_model_available"] and status["retrieval_service_available"]
    
    print("-" * 50)
    if rag_available:
        print("RAG服务整体状态: 可用")
        
        # 打印服务器信息
        if vector_store:
            print(f"Milvus服务器信息: {vector_store.host}:{vector_store.port}")
    else:
        print("RAG服务整体状态: 不可用")
        
        # 构建详细信息
        unavailable_components = []
        if not status["vector_store_available"]:
            unavailable_components.append("向量存储不可用")
        if not status["embedding_model_available"]:
            unavailable_components.append("嵌入模型不可用")
        if not status["retrieval_service_available"]:
            unavailable_components.append("检索服务不可用")
            
        if unavailable_components:
            print("不可用组件: " + ", ".join(unavailable_components))

if __name__ == "__main__":
    check_rag_status() 