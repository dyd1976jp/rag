import os
import sys
import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import unittest

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_mongodb_client
from app.core.vector_store import get_vector_store
from app.rag.models import Document
from langchain_core.documents import Document as LangchainDocument

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('document_validation.log')
    ]
)
logger = logging.getLogger(__name__)

def load_split_results(split_output_path: str) -> Dict[str, Any]:
    """加载分割结果文件"""
    try:
        with open(split_output_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载分割结果失败: {str(e)}")
        return {}

def get_mongodb_documents() -> List[Dict[str, Any]]:
    """从MongoDB获取所有文档"""
    try:
        mongodb_client = get_mongodb_client()
        db = mongodb_client.get_database("rag_db")
        docs_collection = db.get_collection("documents")
        
        # 获取所有文档
        documents = list(docs_collection.find({}))
        
        # 统计父子文档数量
        parent_count = sum(1 for doc in documents if doc.get("metadata", {}).get("is_parent", False))
        child_count = sum(1 for doc in documents if doc.get("metadata", {}).get("is_child", False))
        
        logger.info(f"从MongoDB读取到 {len(documents)} 个文档")
        logger.info(f"父文档: {parent_count}, 子文档: {child_count}")
        
        return documents
    except Exception as e:
        logger.error(f"从MongoDB获取文档失败: {str(e)}")
        return []

def get_vector_documents() -> List[Dict[str, Any]]:
    """从向量存储获取所有文档"""
    try:
        vector_store = get_vector_store()
        
        # 使用一个通用查询获取所有文档
        # 这里使用一个空查询，获取尽可能多的文档
        results = vector_store.similarity_search(
            "这是一个通用查询用于获取所有文档",
            k=1000  # 设置一个较大的k值
        )
        
        # 统计父子文档数量
        parent_count = sum(1 for doc in results if doc.metadata.get("is_parent", False))
        child_count = sum(1 for doc in results if doc.metadata.get("is_child", False))
        
        logger.info(f"从向量存储读取到 {len(results)} 个文档")
        logger.info(f"父文档: {parent_count}, 子文档: {child_count}")
        
        return results
    except Exception as e:
        logger.error(f"从向量存储获取文档失败: {str(e)}")
        return []

def compare_documents(split_docs: Dict[str, Any], mongo_docs: List[Dict[str, Any]], vector_docs: List[Dict[str, Any]]):
    """比较文档一致性"""
    try:
        logger.info("\n=== 开始文档一致性比较 ===")
        
        # 1. 检查文档数量
        split_parent_count = len(split_docs.get("parent_documents", []))
        split_child_count = sum(len(parent.get("children", [])) for parent in split_docs.get("parent_documents", []))
        
        mongo_parent_count = sum(1 for doc in mongo_docs if doc.get("metadata", {}).get("is_parent", False))
        mongo_child_count = sum(1 for doc in mongo_docs if doc.get("metadata", {}).get("is_child", False))
        
        vector_parent_count = sum(1 for doc in vector_docs if doc.metadata.get("is_parent", False))
        vector_child_count = sum(1 for doc in vector_docs if doc.metadata.get("is_child", False))
        
        logger.info("\n文档数量比较:")
        logger.info(f"分割结果 - 父文档: {split_parent_count}, 子文档: {split_child_count}")
        logger.info(f"MongoDB - 父文档: {mongo_parent_count}, 子文档: {mongo_child_count}")
        logger.info(f"向量存储 - 父文档: {vector_parent_count}, 子文档: {vector_child_count}")
        
        # 2. 检查文档ID一致性
        split_parent_ids = {parent["metadata"]["doc_id"] for parent in split_docs.get("parent_documents", [])}
        split_child_ids = {child["metadata"]["doc_id"] 
                          for parent in split_docs.get("parent_documents", [])
                          for child in parent.get("children", [])}
        
        mongo_parent_ids = {str(doc["metadata"]["doc_id"]) 
                           for doc in mongo_docs 
                           if doc.get("metadata", {}).get("is_parent", False)}
        mongo_child_ids = {str(doc["metadata"]["doc_id"]) 
                          for doc in mongo_docs 
                          if doc.get("metadata", {}).get("is_child", False)}
        
        vector_parent_ids = {doc.metadata.get("id") 
                            for doc in vector_docs 
                            if doc.metadata.get("is_parent", False)}
        vector_child_ids = {doc.metadata.get("id") 
                           for doc in vector_docs 
                           if doc.metadata.get("is_child", False)}
        
        # 3. 检查ID一致性
        logger.info("\nID一致性检查:")
        
        # 父文档ID比较
        missing_parent_in_mongo = split_parent_ids - mongo_parent_ids
        missing_parent_in_vector = split_parent_ids - vector_parent_ids
        
        if missing_parent_in_mongo:
            logger.warning(f"MongoDB中缺少的父文档ID: {missing_parent_in_mongo}")
        if missing_parent_in_vector:
            logger.warning(f"向量存储中缺少的父文档ID: {missing_parent_in_vector}")
            
        # 子文档ID比较
        missing_child_in_mongo = split_child_ids - mongo_child_ids
        missing_child_in_vector = split_child_ids - vector_child_ids
        
        if missing_child_in_mongo:
            logger.warning(f"MongoDB中缺少的子文档ID: {missing_child_in_mongo}")
        if missing_child_in_vector:
            logger.warning(f"向量存储中缺少的子文档ID: {missing_child_in_vector}")
        
        # 4. 检查父子关系一致性
        logger.info("\n父子关系一致性检查:")
        for parent in split_docs.get("parent_documents", []):
            parent_id = parent["metadata"]["doc_id"]
            split_children = {child["metadata"]["doc_id"] for child in parent.get("children", [])}
            
            # 检查MongoDB中的父子关系
            mongo_children = {str(doc["metadata"]["doc_id"]) 
                            for doc in mongo_docs 
                            if doc.get("metadata", {}).get("parent_id") == parent_id}
            
            # 检查向量存储中的父子关系
            vector_children = {doc.metadata.get("id") 
                             for doc in vector_docs 
                             if doc.metadata.get("parent_id") == parent_id}
            
            if split_children != mongo_children:
                logger.warning(f"父文档 {parent_id} 的子文档在MongoDB中不匹配")
                logger.warning(f"期望的子文档: {split_children}")
                logger.warning(f"实际的子文档: {mongo_children}")
                
            if split_children != vector_children:
                logger.warning(f"父文档 {parent_id} 的子文档在向量存储中不匹配")
                logger.warning(f"期望的子文档: {split_children}")
                logger.warning(f"实际的子文档: {vector_children}")
        
        # 5. 生成验证报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "document_counts": {
                "split_results": {"parents": split_parent_count, "children": split_child_count},
                "mongodb": {"parents": mongo_parent_count, "children": mongo_child_count},
                "vector_store": {"parents": vector_parent_count, "children": vector_child_count}
            },
            "missing_documents": {
                "mongodb": {
                    "parents": list(missing_parent_in_mongo),
                    "children": list(missing_child_in_mongo)
                },
                "vector_store": {
                    "parents": list(missing_parent_in_vector),
                    "children": list(missing_child_in_vector)
                }
            }
        }
        
        # 保存报告
        report_path = "validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"\n验证报告已保存到: {report_path}")
        
    except Exception as e:
        logger.error(f"比较文档时出错: {str(e)}")
        raise

def main():
    """主函数"""
    try:
        # 1. 加载分割结果
        split_output_path = "backend/data/split_results.json"
        split_docs = load_split_results(split_output_path)
        if not split_docs:
            logger.error("无法加载分割结果文件")
            return
            
        # 2. 获取MongoDB中的文档
        mongo_docs = get_mongodb_documents()
        if not mongo_docs:
            logger.error("无法从MongoDB获取文档")
            return
            
        # 3. 获取向量存储中的文档
        vector_docs = get_vector_documents()
        if not vector_docs:
            logger.error("无法从向量存储获取文档")
            return
            
        # 4. 比较文档
        compare_documents(split_docs, mongo_docs, vector_docs)
        
    except Exception as e:
        logger.error(f"验证过程失败: {str(e)}")
        raise

class TestDocumentValidation(unittest.TestCase):
    def setUp(self):
        """测试准备"""
        # 使用项目根目录下的data目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.test_dir = project_root / "data" / "test_data"
        self.output_dir = project_root / "data" / "results"
        
        # 创建必要的目录
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置输出路径
        self.split_output_path = self.output_dir / "split_results.json"

if __name__ == "__main__":
    main() 