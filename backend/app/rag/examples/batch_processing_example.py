"""
批量处理器使用示例
演示如何使用BatchProcessor进行高效的批量操作
"""

import asyncio
import logging
from typing import List
from pathlib import Path

from ..batch_processor import BatchProcessor, BatchConfig, BatchStrategy
from ..models import Document
from ..index_processor import ParentChildIndexProcessor, ProcessRule
from ..vector_store import MilvusVectorStore
from ..document_store import DocumentStore
from ..embedding_model import EmbeddingModel
from ..enhanced_retriever import EnhancedRetriever, RetrievalConfig
from ..parallel_retriever import ParallelRetriever

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def batch_processing_demo():
    """批量处理演示"""
    
    # 1. 初始化组件
    logger.info("初始化批量处理组件...")
    
    # 创建模拟组件（实际使用时需要真实的组件）
    index_processor = ParentChildIndexProcessor()
    vector_store = MilvusVectorStore()
    document_store = None  # DocumentStore(db)
    embedding_model = EmbeddingModel()
    enhanced_retriever = EnhancedRetriever(vector_store, embedding_model)
    parallel_retriever = ParallelRetriever(enhanced_retriever)
    
    # 创建批量处理器
    batch_processor = BatchProcessor(
        index_processor=index_processor,
        vector_store=vector_store,
        document_store=document_store,
        embedding_model=embedding_model,
        enhanced_retriever=enhanced_retriever,
        parallel_retriever=parallel_retriever
    )
    
    # 2. 准备测试数据
    logger.info("准备测试文档...")
    test_documents = [
        Document(
            page_content=f"这是第{i}个测试文档的内容。包含了关于人工智能、机器学习和自然语言处理的相关信息。",
            metadata={
                "id": f"doc_{i}",
                "title": f"测试文档{i}",
                "source": "batch_demo",
                "category": "AI" if i % 2 == 0 else "ML"
            }
        )
        for i in range(1, 101)  # 创建100个测试文档
    ]
    
    # 3. 演示不同的批量处理策略
    await demo_batch_strategies(batch_processor, test_documents)
    
    # 4. 演示批量索引
    await demo_batch_indexing(batch_processor, test_documents[:20])
    
    # 5. 演示批量检索
    await demo_batch_retrieval(batch_processor)
    
    # 6. 演示批量更新和删除
    await demo_batch_update_delete(batch_processor, test_documents[:10])
    
    # 7. 演示进度跟踪
    await demo_progress_tracking(batch_processor, test_documents[:30])


async def demo_batch_strategies(batch_processor: BatchProcessor, documents: List[Document]):
    """演示不同的批量处理策略"""
    logger.info("\n=== 批量处理策略演示 ===")
    
    strategies = [
        (BatchStrategy.SEQUENTIAL, "顺序处理"),
        (BatchStrategy.PARALLEL, "并行处理"),
        (BatchStrategy.ADAPTIVE, "自适应处理"),
        (BatchStrategy.MEMORY_OPTIMIZED, "内存优化处理")
    ]
    
    for strategy, name in strategies:
        logger.info(f"\n--- {name} ---")
        config = BatchConfig(
            strategy=strategy,
            batch_size=10,
            max_workers=4,
            enable_progress_tracking=True
        )
        
        try:
            # 模拟处理函数
            async def mock_process_single_document(doc, rule):
                await asyncio.sleep(0.001)  # 模拟处理时间
                return doc
            
            batch_processor._process_single_document = mock_process_single_document
            
            result = await batch_processor.batch_process_documents(
                documents[:20], None, config
            )
            
            logger.info(f"策略: {name}")
            logger.info(f"处理成功: {result['processed_count']} 个文档")
            logger.info(f"处理失败: {result['failed_count']} 个文档")
            logger.info(f"处理时间: {result['processing_time']:.2f} 秒")
            
        except Exception as e:
            logger.error(f"{name} 处理失败: {e}")


async def demo_batch_indexing(batch_processor: BatchProcessor, documents: List[Document]):
    """演示批量索引"""
    logger.info("\n=== 批量索引演示 ===")
    
    config = BatchConfig(
        strategy=BatchStrategy.PARALLEL,
        batch_size=5,
        max_workers=2,
        enable_progress_tracking=True
    )
    
    try:
        result = await batch_processor.batch_index_documents(documents, config)
        
        logger.info(f"索引成功: {result['indexed_count']} 个文档")
        logger.info(f"索引失败: {result['failed_count']} 个文档")
        logger.info(f"索引时间: {result['processing_time']:.2f} 秒")
        
        if result['failed_docs']:
            logger.warning(f"失败的文档: {len(result['failed_docs'])} 个")
            
    except Exception as e:
        logger.error(f"批量索引失败: {e}")


async def demo_batch_retrieval(batch_processor: BatchProcessor):
    """演示批量检索"""
    logger.info("\n=== 批量检索演示 ===")
    
    queries = [
        "人工智能的发展历史",
        "机器学习算法分类",
        "自然语言处理技术",
        "深度学习应用场景",
        "神经网络结构设计"
    ]
    
    config = BatchConfig(
        max_workers=3,
        timeout_seconds=30.0
    )
    
    retrieval_config = RetrievalConfig(
        top_k=5,
        method="hybrid",
        enable_reranking=True
    )
    
    try:
        result = await batch_processor.batch_retrieve(
            queries, config, retrieval_config
        )
        
        logger.info(f"检索查询数: {result['query_count']}")
        logger.info(f"检索结果数: {len(result['results'])}")
        logger.info(f"检索时间: {result['processing_time']:.2f} 秒")
        
        # 显示部分结果
        for i, query in enumerate(queries[:3]):
            results = result['results'][i] if i < len(result['results']) else []
            logger.info(f"查询 '{query}' 返回 {len(results)} 个结果")
            
    except Exception as e:
        logger.error(f"批量检索失败: {e}")


async def demo_batch_update_delete(batch_processor: BatchProcessor, documents: List[Document]):
    """演示批量更新和删除"""
    logger.info("\n=== 批量更新和删除演示 ===")
    
    config = BatchConfig(batch_size=3)
    
    # 批量更新
    try:
        # 修改文档内容
        updated_docs = []
        for doc in documents:
            updated_doc = Document(
                page_content=doc.page_content + " [已更新]",
                metadata={**doc.metadata, "updated": True}
            )
            updated_docs.append(updated_doc)
        
        update_result = await batch_processor.batch_update_documents(updated_docs, config)
        logger.info(f"更新成功: {update_result['updated_count']} 个文档")
        logger.info(f"更新失败: {update_result['failed_count']} 个文档")
        
    except Exception as e:
        logger.error(f"批量更新失败: {e}")
    
    # 批量删除
    try:
        doc_ids = [doc.metadata["id"] for doc in documents]
        delete_result = await batch_processor.batch_delete_documents(doc_ids, config)
        
        logger.info(f"删除成功: {delete_result['deleted_count']} 个文档")
        logger.info(f"删除失败: {delete_result['failed_count']} 个文档")
        
        if delete_result['failed_ids']:
            logger.warning(f"删除失败的ID: {delete_result['failed_ids']}")
            
    except Exception as e:
        logger.error(f"批量删除失败: {e}")


async def demo_progress_tracking(batch_processor: BatchProcessor, documents: List[Document]):
    """演示进度跟踪"""
    logger.info("\n=== 进度跟踪演示 ===")
    
    # 添加进度回调
    def progress_callback(progress):
        logger.info(
            f"进度: {progress.progress_percentage:.1f}% "
            f"({progress.processed_items}/{progress.total_items}) "
            f"批次: {progress.current_batch}/{progress.total_batches} "
            f"预计剩余: {progress.estimated_remaining_time:.1f}秒"
        )
    
    batch_processor.add_progress_callback(progress_callback)
    
    config = BatchConfig(
        strategy=BatchStrategy.SEQUENTIAL,
        batch_size=5,
        enable_progress_tracking=True,
        checkpoint_interval=2  # 每2个批次保存检查点
    )
    
    try:
        # 模拟处理函数
        async def mock_process_single_document(doc, rule):
            await asyncio.sleep(0.1)  # 模拟较长的处理时间
            return doc
        
        batch_processor._process_single_document = mock_process_single_document
        
        result = await batch_processor.batch_process_documents(documents, None, config)
        
        logger.info(f"最终进度: {batch_processor.get_progress().progress_percentage:.1f}%")
        logger.info(f"检查点数量: {len(batch_processor.get_checkpoints())}")
        
    except Exception as e:
        logger.error(f"进度跟踪演示失败: {e}")


def demo_configuration_options():
    """演示配置选项"""
    logger.info("\n=== 配置选项演示 ===")
    
    # 基本配置
    basic_config = BatchConfig()
    logger.info(f"默认配置: {basic_config}")
    
    # 高性能配置
    high_performance_config = BatchConfig(
        strategy=BatchStrategy.PARALLEL,
        batch_size=50,
        max_workers=8,
        timeout_seconds=600.0,
        enable_progress_tracking=True
    )
    logger.info(f"高性能配置: {high_performance_config}")
    
    # 内存优化配置
    memory_optimized_config = BatchConfig(
        strategy=BatchStrategy.MEMORY_OPTIMIZED,
        batch_size=10,
        memory_limit_mb=512,
        enable_error_recovery=True,
        retry_failed_batches=True,
        max_retries=3
    )
    logger.info(f"内存优化配置: {memory_optimized_config}")
    
    # 错误恢复配置
    error_recovery_config = BatchConfig(
        enable_error_recovery=True,
        retry_failed_batches=True,
        max_retries=5,
        checkpoint_interval=5
    )
    logger.info(f"错误恢复配置: {error_recovery_config}")


async def main():
    """主函数"""
    logger.info("开始批量处理演示...")
    
    try:
        # 演示配置选项
        demo_configuration_options()
        
        # 运行批量处理演示
        await batch_processing_demo()
        
        logger.info("\n批量处理演示完成！")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
