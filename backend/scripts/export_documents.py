from app.core.database import get_mongodb_client
from app.core.vector_store import get_vector_store
from app.core.embedding import get_embedding_model
from app.rag.document_splitter import HierarchicalDocumentSplitter
from app.rag.models import Document
from loguru import logger
import json
from datetime import datetime
from pathlib import Path

def export_documents():
    """导出所有文档数据为JSON格式"""
    try:
        # 连接MongoDB
        db = get_mongodb_client()
        documents_collection = db["documents"]
        
        # 获取所有文档
        all_docs = list(documents_collection.find())
        logger.info(f"找到 {len(all_docs)} 个文档")
        
        # 创建层级分割器
        splitter = HierarchicalDocumentSplitter()
        
        # 处理每个文档
        processed_documents = []
        for doc in all_docs:
            # 创建Document对象
            document = Document(
                page_content=doc.get('content', ''),
                metadata=doc.get('metadata', {})
            )
            
            # 使用层级分割器处理文档
            try:
                segments = splitter.split_document(document)
                if segments:
                    for segment in segments:
                        processed_doc = {
                            'content': segment.page_content,
                            'metadata': segment.metadata,
                            'children': []
                        }
                        
                        # 如果有子文档，添加到children列表
                        if hasattr(segment, 'children') and segment.children:
                            for child in segment.children:
                                child_doc = {
                                    'content': child.page_content,
                                    'metadata': child.metadata
                                }
                                processed_doc['children'].append(child_doc)
                                
                        processed_documents.append(processed_doc)
            except Exception as e:
                logger.warning(f"处理文档时出错: {str(e)}")
                continue
        
        # 创建输出目录
        output_dir = Path('data/exports')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'documents_export_{timestamp}.json'
        
        # 统计信息
        total_children = sum(len(doc.get('children', [])) for doc in processed_documents)
        
        # 保存为JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_documents': len(all_docs),
                'processed_documents': len(processed_documents),
                'total_children': total_children,
                'documents': processed_documents
            }, f, ensure_ascii=False, indent=2)
            
        logger.info(f"数据已导出到文件: {output_file}")
        logger.info(f"总文档数: {len(all_docs)}")
        logger.info(f"处理后的文档数: {len(processed_documents)}")
        logger.info(f"子文档总数: {total_children}")
        
    except Exception as e:
        logger.error(f"导出文档时出错: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("开始导出文档数据...")
    export_documents()
    logger.info("导出完成") 