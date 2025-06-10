"""
测试文档分割功能的脚本
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.document_splitter import DocumentSplitter, HierarchicalDocumentSplitter
from app.rag.document_processor import Document
from app.rag.models import DocumentSegment, ChildChunk
from app.rag.database import MongoDBManager
from app.rag.vector_store import MilvusVectorStore
from app.rag.embedding_model import EmbeddingModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_text_splitting():
    """测试文本分割功能"""
    # 设置环境变量
    os.environ["CHUNK_SIZE"] = "100"  # 设置较小的分块大小以便于观察
    os.environ["CHUNK_OVERLAP"] = "20"  # 设置重叠大小
    os.environ["SPLIT_BY_PARAGRAPH"] = "true"  # 启用段落分割
    os.environ["SPLIT_BY_SENTENCE"] = "true"  # 启用句子分割
    
    # 创建示例文本
    test_text = """
第一段落：这是第一段文字。这里包含了一些基本信息。这是第一段的最后一句。

第二段落：这是第二段的开始。这里有一些技术细节的描述。
这是第二段的第二行。这里继续描述一些内容。

第三段落：这是最后一段。这段包含总结信息。
这是最后一段的第二行。这里是文档的结束。
    """
    
    # 创建文档对象
    doc = Document(
        page_content=test_text,
        metadata={
            "source": "test_document",
            "created_at": "2024-03-19"
        }
    )
    
    # 创建分割器实例
    splitter = DocumentSplitter()
    
    logger.info("开始测试文档分割...")
    logger.info(f"分割配置: chunk_size={splitter.chunk_size}, chunk_overlap={splitter.chunk_overlap}")
    logger.info(f"原始文本长度: {len(test_text)} 字符")
    
    # 执行分割
    try:
        segments = splitter.split_document(doc)
        
        # 打印分割结果
        logger.info(f"\n分割结果: 共生成 {len(segments)} 个片段")
        for i, segment in enumerate(segments, 1):
            logger.info(f"\n片段 {i}:")
            logger.info(f"内容: {segment.page_content}")
            logger.info(f"长度: {len(segment.page_content)} 字符")
            logger.info(f"元数据: {segment.metadata}")
            
        # 验证分割结果
        total_chars = sum(len(seg.page_content) for seg in segments)
        avg_length = total_chars / len(segments) if segments else 0
        
        logger.info(f"\n统计信息:")
        logger.info(f"总字符数: {total_chars}")
        logger.info(f"平均片段长度: {avg_length:.2f} 字符")
        logger.info(f"最短片段长度: {min(len(seg.page_content) for seg in segments)} 字符")
        logger.info(f"最长片段长度: {max(len(seg.page_content) for seg in segments)} 字符")
        
    except Exception as e:
        logger.error(f"分割过程中出错: {str(e)}")
        raise

def test_different_configurations():
    """测试不同的分割配置"""
    test_text = """
这是一个测试文档。它包含多个句子和段落。
这是第一段的第二句话。这是第三句话。

这是第二段。它也有多个句子。
这是一个较长的句子，包含了更多的信息和细节描述。

这是最后一段。
它很短。
    """
    
    doc = Document(page_content=test_text, metadata={"source": "test_config"})
    
    # 测试不同的配置
    configs = [
        {
            "CHUNK_SIZE": "50",
            "CHUNK_OVERLAP": "10",
            "SPLIT_BY_PARAGRAPH": "true",
            "SPLIT_BY_SENTENCE": "true"
        },
        {
            "CHUNK_SIZE": "100",
            "CHUNK_OVERLAP": "20",
            "SPLIT_BY_PARAGRAPH": "true",
            "SPLIT_BY_SENTENCE": "false"
        },
        {
            "CHUNK_SIZE": "200",
            "CHUNK_OVERLAP": "30",
            "SPLIT_BY_PARAGRAPH": "false",
            "SPLIT_BY_SENTENCE": "true"
        }
    ]
    
    for config in configs:
        logger.info(f"\n测试配置: {config}")
        
        # 设置环境变量
        for key, value in config.items():
            os.environ[key] = value
            
        splitter = DocumentSplitter()
        
        try:
            segments = splitter.split_document(doc)
            logger.info(f"生成片段数: {len(segments)}")
            for i, segment in enumerate(segments, 1):
                logger.info(f"片段 {i} 长度: {len(segment.page_content)} 字符")
                logger.info(f"内容: {segment.page_content}\n")
        except Exception as e:
            logger.error(f"使用配置 {config} 分割时出错: {str(e)}")

def test_hierarchical_splitting():
    """测试父子分割功能"""
    # 创建示例文本
    test_text = """
第一章：引言
这是一个较长的文档示例。它包含多个章节和段落。
这个文档将用于测试父子分割功能。每个章节都可能被分成父块。
每个父块又可以进一步分割成更小的子块。

第二章：主要内容
这一章包含了更多的细节信息。我们将详细讨论父子分割的原理。
父块通常是较大的文本单位，比如章节或者大段落。
子块则是更小的文本单位，可能是句子或者短段落。

第三章：技术实现
在实现层面，我们使用了两级分割策略。
第一级分割会将文档分成较大的块，这些是父块。
第二级分割则会将这些父块进一步分割成更小的子块。
这种方式可以更好地保持文档的层级结构。

第四章：总结
父子分割方法提供了更灵活的文档处理方式。
它可以同时保持文档的整体结构和局部细节。
这对于后续的文档分析和处理非常有帮助。
    """
    
    # 创建文档对象
    doc = Document(
        page_content=test_text,
        metadata={
            "source": "test_hierarchical",
            "created_at": "2024-03-19",
            "document_type": "technical"
        }
    )
    
    # 创建层级分割器实例
    splitter = HierarchicalDocumentSplitter(
        parent_chunk_size=1024,
        parent_chunk_overlap=200,
        parent_separator="\n\n",
        child_chunk_size=512,
        child_chunk_overlap=50,
        child_separator="\n"
    )
    
    logger.info("\n=== 开始测试父子分割 ===")
    logger.info(f"父块配置: chunk_size=1024, chunk_overlap=200, separator=\\n\\n")
    logger.info(f"子块配置: chunk_size=512, chunk_overlap=50, separator=\\n")
    logger.info(f"原始文本长度: {len(test_text)} 字符")
    
    try:
        # 执行文档分割
        parent_docs = splitter.split_document(doc)
        
        logger.info(f"\n生成父文档数量: {len(parent_docs)}")
        
        # 显示父文档信息
        for i, parent in enumerate(parent_docs, 1):
            logger.info(f"\n父文档 {i}:")
            logger.info(f"ID: {parent.metadata.get('doc_id', 'N/A')}")
            logger.info(f"哈希: {parent.metadata.get('doc_hash', 'N/A')}")
            logger.info(f"内容长度: {len(parent.page_content)} 字符")
            logger.info(f"内容预览: {parent.page_content[:100]}...")
            
            # 显示子文档信息
            if hasattr(parent, 'children') and parent.children:
                logger.info(f"\n  子文档数量: {len(parent.children)}")
                
                for j, child in enumerate(parent.children, 1):
                    logger.info(f"\n  子文档 {j}:")
                    logger.info(f"  ID: {child.metadata.get('doc_id', 'N/A')}")
                    logger.info(f"  哈希: {child.metadata.get('doc_hash', 'N/A')}")
                    logger.info(f"  内容长度: {len(child.page_content)} 字符")
                    logger.info(f"  内容: {child.page_content}")
        
        # 计算统计信息
        total_parent_chars = sum(len(p.page_content) for p in parent_docs)
        total_children = sum(len(p.children) if hasattr(p, 'children') and p.children else 0 for p in parent_docs)
        avg_parent_size = total_parent_chars / len(parent_docs) if parent_docs else 0
        
        logger.info(f"\n统计信息:")
        logger.info(f"总父文档数: {len(parent_docs)}")
        logger.info(f"总子文档数: {total_children}")
        logger.info(f"平均父文档大小: {avg_parent_size:.2f} 字符")
        logger.info(f"父文档覆盖率: {total_parent_chars/len(test_text)*100:.2f}%")
        
    except Exception as e:
        logger.error(f"父子分割测试失败: {str(e)}")
        raise

def test_document_storage():
    """测试文档分割结果的数据库存储"""
    logger.info("\n=== 测试数据库存储 ===")
    
    # 初始化数据库管理器
    try:
        db_manager = MongoDBManager()
        logger.info("MongoDB连接成功")
        
        # 初始化向量存储
        vector_store = MilvusVectorStore()
        logger.info("Milvus连接成功")
        
        # 初始化嵌入模型
        embedding_model = EmbeddingModel()
        logger.info("嵌入模型初始化成功")
        
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        return
    
    # 创建测试文档
    test_text = """
这是一个测试文档，用于验证存储功能。这里包含多个句子。每个句子都可能成为一个子块。
    """
    
    doc = Document(
        page_content=test_text,
        metadata={
            "source": "test_storage",
            "created_at": "2024-03-19"
        }
    )
    
    # 创建分割器
    splitter = HierarchicalDocumentSplitter()
    
    try:
        # 执行分割
        parent_docs = splitter.split_document(doc)
        logger.info(f"生成了 {len(parent_docs)} 个父文档")
        
        # 存储父文档和子文档
        for parent in parent_docs:
            # 存储父文档到MongoDB
            result = db_manager.save_document(parent)
            logger.info(f"存储父文档到MongoDB {parent.metadata['doc_id']}: {result}")
            
            # 获取父文档的嵌入向量
            parent_embedding = embedding_model.embed_documents([parent.page_content])[0]
            
            # 存储父文档到Milvus
            result = vector_store.add_documents([{
                "id": parent.metadata["doc_id"],
                "content": parent.page_content,
                "embedding": parent_embedding,
                "metadata": parent.metadata
            }])
            logger.info(f"存储父文档到Milvus {parent.metadata['doc_id']}: {result}")
            
            # 存储子文档
            if parent.children:
                for child in parent.children:
                    # 存储子文档到MongoDB
                    result = db_manager.save_document(child)
                    logger.info(f"存储子文档到MongoDB {child.metadata['doc_id']}: {result}")
                    
                    # 获取子文档的嵌入向量
                    child_embedding = embedding_model.embed_documents([child.page_content])[0]
                    
                    # 存储子文档到Milvus
                    result = vector_store.add_documents([{
                        "id": child.metadata["doc_id"],
                        "content": child.page_content,
                        "embedding": child_embedding,
                        "metadata": child.metadata
                    }])
                    logger.info(f"存储子文档到Milvus {child.metadata['doc_id']}: {result}")
        
        # 验证存储结果
        for parent in parent_docs:
            # 检查MongoDB中的父文档
            stored_parent = db_manager.get_document(parent.metadata["doc_id"])
            if stored_parent:
                logger.info(f"成功从MongoDB检索到父文档: {parent.metadata['doc_id']}")
                
                # 检查MongoDB中的子文档
                child_docs = db_manager.get_documents(parent.metadata["doc_id"])
                logger.info(f"从MongoDB检索到 {len(child_docs)} 个子文档")
                
                # 检查Milvus中的父文档
                similar_parents = vector_store.similarity_search(
                    parent.page_content,
                    k=1,
                    filter={"id": parent.metadata["doc_id"]}
                )
                if similar_parents:
                    logger.info(f"成功从Milvus检索到父文档: {parent.metadata['doc_id']}")
                
                # 检查每个子文档在Milvus中的存储
                for child in child_docs:
                    similar_children = vector_store.similarity_search(
                        child.page_content,
                        k=1,
                        filter={"metadata.doc_id": child.metadata["doc_id"]}
                    )
                    if similar_children:
                        logger.info(f"成功从Milvus检索到子文档: {child.metadata['doc_id']}")
            else:
                logger.error(f"未找到父文档: {parent.metadata['doc_id']}")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        raise
    finally:
        # 关闭数据库连接
        db_manager.close()
        # Milvus不需要显式关闭连接

def main():
    """主函数"""
    logger.info("开始文档分割测试")
    
    # 测试基本文本分割
    logger.info("\n=== 测试基本文本分割 ===")
    test_text_splitting()
    
    # 测试不同配置
    logger.info("\n=== 测试不同配置 ===")
    test_different_configurations()
    
    # 测试父子分割
    logger.info("\n=== 测试父子分割 ===")
    test_hierarchical_splitting()
    
    # 测试数据库存储
    logger.info("\n=== 测试数据库存储 ===")
    test_document_storage()
    
    logger.info("\n测试完成")

if __name__ == "__main__":
    main() 