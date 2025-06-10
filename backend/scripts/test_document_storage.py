import os
import sys
import json
import logging
from typing import Dict, Any
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.document_splitter import HierarchicalDocumentSplitter
from app.rag.models import Document
from app.utils.pdf_utils import extract_text_from_pdf
from app.core.database import get_mongodb_client
from app.core.vector_store import get_vector_store, clear as clear_vector_store
from app.core.embedding import get_embedding_model
from langchain_core.documents import Document as LangchainDocument

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_document_storage(pdf_path: str):
    """测试文档存储功能"""
    try:
        logger.info("\n=== 开始测试文档存储 ===")
        logger.info(f"处理PDF文件: {pdf_path}")
        
        # 初始化数据库连接
        db = get_mongodb_client()
        documents_collection = db["documents"]
        logger.info("MongoDB连接成功")
        
        # 初始化嵌入模型
        embedding_model = get_embedding_model()
        logger.info("嵌入模型连接成功，使用API: http://192.168.1.30:1234/v1")
        
        # 清理已有数据
        logger.info("清理已有数据...")
        documents_collection.delete_many({})
        clear_vector_store()
        
        # 重新初始化向量存储
        vector_store = get_vector_store(embedding_model)
        logger.info("向量存储重新初始化成功")
        
        # 提取PDF文本
        text = extract_text_from_pdf(pdf_path)
        logger.info(f"提取的文本长度: {len(text)} 字符")
        
        # 创建文档对象
        document = Document(
            page_content=text,
            metadata={
                "source": os.path.basename(pdf_path),
                "file_type": "pdf",
                "test_type": "storage_test"
            }
        )
        
        # 分割文档
        splitter = HierarchicalDocumentSplitter()
        parent_docs = splitter.split_document(document)
        logger.info(f"文档分割完成，生成 {len(parent_docs)} 个父文档")
        
        # 保存分割结果到文件
        split_results = {
            "parent_docs": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in parent_docs
            ]
        }
        split_output_path = "backend/data/split_results.json"
        with open(split_output_path, "w", encoding="utf-8") as f:
            json.dump(split_results, f, ensure_ascii=False, indent=2)
        logger.info(f"分割结果已保存到 {split_output_path}")
        
        # 存储父文档
        parent_embeddings = []
        for doc in parent_docs:
            # 转换为LangChain文档格式
            langchain_doc = LangchainDocument(
                page_content=doc.page_content,
                metadata=doc.metadata
            )
            
            # 生成文档向量
            doc_embedding = embedding_model.embed_documents([doc.page_content])[0]
            parent_embeddings.append(doc_embedding)
            
            # 存储到MongoDB
            doc_id = doc.metadata.get("doc_id")
            documents_collection.insert_one({
                "doc_id": doc_id,
                "content": doc.page_content,
                "metadata": doc.metadata,
                "type": "parent"
            })
            logger.info(f"存储父文档成功: {doc_id}")
            
            # 存储到向量数据库
            vector_store.add_documents([langchain_doc], embeddings=[doc_embedding], ids=[doc_id])
        
        # 统计存储结果
        logger.info("\n=== 存储结果统计 ===")
        parent_count = len(parent_docs)
        stored_parent_count = documents_collection.count_documents({"type": "parent"})
        parent_vector_count = len(parent_embeddings)
        
        logger.info(f"总父文档数: {parent_count}")
        logger.info(f"已存储父文档数: {stored_parent_count}")
        logger.info(f"父文档向量数: {parent_vector_count}")
        
        # 验证文档检索
        logger.info("\n=== 验证文档检索 ===")
        total_docs = documents_collection.count_documents({})
        parent_docs = documents_collection.count_documents({"type": "parent"})
        child_docs = documents_collection.count_documents({"type": "child"})
        
        logger.info(f"MongoDB中的文档总数: {total_docs}")
        logger.info(f"MongoDB中的父文档数: {parent_docs}")
        logger.info(f"MongoDB中的子文档数: {child_docs}")
        
        # 测试向量检索
        test_query = "汽车安全性能"
        logger.info(f"\n使用测试查询 '{test_query}' 检索相似文档:")
        
        similar_docs = vector_store.similarity_search_with_score(test_query, k=3)
        
        for i, (doc, score) in enumerate(similar_docs, 1):
            logger.info(f"\n--- 相似文档 {i} ---")
            logger.info(f"内容: {doc.page_content[:200]}...")
            logger.info(f"相似度得分: {score}")
            logger.info(f"文档ID: {doc.metadata.get('doc_id', 'N/A')}")
            
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        raise

if __name__ == "__main__":
    # 设置PDF文件路径
    pdf_path = "data/uploads/初赛训练数据集.pdf"
    
    # 运行测试
    test_document_storage(pdf_path) 