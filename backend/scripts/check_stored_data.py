from app.core.database import get_mongodb_client
from app.core.vector_store import get_vector_store
from app.core.embedding import get_embedding_model
from loguru import logger
import json

def check_mongodb_documents():
    """检查MongoDB中存储的文档"""
    try:
        # 连接MongoDB
        db = get_mongodb_client()
        documents_collection = db["documents"]
        
        # 获取所有文档
        docs = list(documents_collection.find())
        logger.info(f"\n=== MongoDB中的文档 (总数: {len(docs)}) ===")
        
        for i, doc in enumerate(docs[:5], 1):  # 只显示前5个文档
            logger.info(f"\n--- 文档 {i} ---")
            logger.info(f"文档ID: {doc.get('_id')}")
            logger.info(f"标题: {doc.get('title', 'N/A')}")
            logger.info(f"内容预览: {doc.get('content', 'N/A')[:200]}...")
            logger.info(f"元数据: {json.dumps(doc.get('metadata', {}), ensure_ascii=False, indent=2)}")
            
    except Exception as e:
        logger.error(f"检查MongoDB文档时出错: {str(e)}")
        raise

def check_vector_store():
    """检查Milvus中存储的向量"""
    try:
        # 初始化向量存储
        embedding_model = get_embedding_model()
        vector_store = get_vector_store(embedding_model)
        
        # 使用一个测试查询来检查向量存储
        test_query = "文档内容概述"
        results = vector_store.similarity_search_with_score(test_query, k=5)
        
        logger.info(f"\n=== Milvus中的向量检索结果 ===")
        logger.info(f"测试查询: '{test_query}'")
        
        for i, (doc, score) in enumerate(results, 1):
            logger.info(f"\n--- 结果 {i} ---")
            logger.info(f"相似度得分: {score}")
            logger.info(f"内容预览: {doc.page_content[:200]}...")
            logger.info(f"元数据: {json.dumps(doc.metadata, ensure_ascii=False, indent=2)}")
            
    except Exception as e:
        logger.error(f"检查向量存储时出错: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("开始检查存储的数据...")
    check_mongodb_documents()
    check_vector_store()
    logger.info("\n数据检查完成") 