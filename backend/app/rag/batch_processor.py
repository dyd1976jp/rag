"""
批量操作优化模块
实现高效的批量文档处理、批量索引创建和批量检索操作
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum
import concurrent.futures
from functools import partial
import math

from .models import Document, DocumentSegment, ChildChunk
from .enhanced_retriever import EnhancedRetriever, RetrievalConfig, RetrievalResult
from .advanced_reranker import AdvancedRerankerService, RerankingConfig
from .parallel_retriever import ParallelRetriever, ParallelConfig
from .index_processor import ParentChildIndexProcessor, ProcessRule
from .vector_store import MilvusVectorStore
from .document_store import DocumentStore
from .embedding_model import EmbeddingModel

logger = logging.getLogger(__name__)


class BatchStrategy(str, Enum):
    """批量处理策略"""
    SEQUENTIAL = "sequential"          # 顺序处理
    PARALLEL = "parallel"             # 并行处理
    ADAPTIVE = "adaptive"             # 自适应策略
    MEMORY_OPTIMIZED = "memory_optimized"  # 内存优化


@dataclass
class BatchConfig:
    """批量处理配置"""
    strategy: BatchStrategy = BatchStrategy.ADAPTIVE
    batch_size: int = 100             # 批处理大小
    max_workers: int = 4              # 最大工作线程数
    memory_limit_mb: int = 1024       # 内存限制(MB)
    timeout_seconds: float = 300.0    # 超时时间
    enable_progress_tracking: bool = True  # 启用进度跟踪
    enable_error_recovery: bool = True     # 启用错误恢复
    retry_failed_batches: bool = True      # 重试失败的批次
    max_retries: int = 3              # 最大重试次数
    checkpoint_interval: int = 10     # 检查点间隔


@dataclass
class BatchProgress:
    """批量处理进度"""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    current_batch: int = 0
    total_batches: int = 0
    start_time: float = 0.0
    estimated_remaining_time: float = 0.0
    
    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        return time.time() - self.start_time
    
    def update_eta(self):
        """更新预计剩余时间"""
        if self.processed_items > 0:
            avg_time_per_item = self.elapsed_time / self.processed_items
            remaining_items = self.total_items - self.processed_items
            self.estimated_remaining_time = avg_time_per_item * remaining_items


class BatchProcessor:
    """批量处理器"""
    
    def __init__(
        self,
        index_processor: ParentChildIndexProcessor,
        vector_store: MilvusVectorStore,
        document_store: DocumentStore,
        embedding_model: EmbeddingModel,
        enhanced_retriever: Optional[EnhancedRetriever] = None,
        parallel_retriever: Optional[ParallelRetriever] = None
    ):
        self.index_processor = index_processor
        self.vector_store = vector_store
        self.document_store = document_store
        self.embedding_model = embedding_model
        self.enhanced_retriever = enhanced_retriever
        self.parallel_retriever = parallel_retriever
        
        # 进度跟踪
        self.progress = BatchProgress()
        self.progress_callbacks: List[Callable[[BatchProgress], None]] = []
        
        # 错误恢复
        self.failed_batches: List[Tuple[int, List[Any], Exception]] = []
        self.checkpoints: Dict[str, Any] = {}
    
    def add_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)
    
    def _update_progress(self):
        """更新进度并调用回调函数"""
        self.progress.update_eta()
        for callback in self.progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.warning(f"进度回调函数执行失败: {e}")
    
    async def batch_process_documents(
        self,
        documents: List[Document],
        process_rule: Optional[ProcessRule] = None,
        config: BatchConfig = None
    ) -> Dict[str, Any]:
        """批量处理文档"""
        if config is None:
            config = BatchConfig()
        
        # 初始化进度
        self.progress = BatchProgress(
            total_items=len(documents),
            total_batches=math.ceil(len(documents) / config.batch_size),
            start_time=time.time()
        )
        
        logger.info(f"开始批量处理 {len(documents)} 个文档，策略: {config.strategy}")
        
        try:
            if config.strategy == BatchStrategy.SEQUENTIAL:
                return await self._sequential_process_documents(documents, process_rule, config)
            elif config.strategy == BatchStrategy.PARALLEL:
                return await self._parallel_process_documents(documents, process_rule, config)
            elif config.strategy == BatchStrategy.ADAPTIVE:
                return await self._adaptive_process_documents(documents, process_rule, config)
            elif config.strategy == BatchStrategy.MEMORY_OPTIMIZED:
                return await self._memory_optimized_process_documents(documents, process_rule, config)
            else:
                raise ValueError(f"不支持的批量处理策略: {config.strategy}")
                
        except Exception as e:
            logger.error(f"批量处理文档失败: {e}")
            raise
    
    async def _sequential_process_documents(
        self,
        documents: List[Document],
        process_rule: Optional[ProcessRule],
        config: BatchConfig
    ) -> Dict[str, Any]:
        """顺序处理文档"""
        processed_docs = []
        failed_docs = []
        
        for i in range(0, len(documents), config.batch_size):
            batch = documents[i:i + config.batch_size]
            self.progress.current_batch = i // config.batch_size + 1
            
            try:
                logger.info(f"处理批次 {self.progress.current_batch}/{self.progress.total_batches}")
                
                # 处理当前批次
                batch_results = []
                for doc in batch:
                    try:
                        # 使用索引处理器处理单个文档
                        processed_doc = await self._process_single_document(doc, process_rule)
                        batch_results.append(processed_doc)
                        self.progress.processed_items += 1
                    except Exception as e:
                        logger.error(f"处理文档失败: {e}")
                        failed_docs.append((doc, str(e)))
                        self.progress.failed_items += 1
                
                processed_docs.extend(batch_results)
                
                # 更新进度
                if config.enable_progress_tracking:
                    self._update_progress()
                
                # 检查点保存
                if config.checkpoint_interval > 0 and self.progress.current_batch % config.checkpoint_interval == 0:
                    await self._save_checkpoint(f"batch_{self.progress.current_batch}", {
                        "processed_docs": len(processed_docs),
                        "failed_docs": len(failed_docs),
                        "current_batch": self.progress.current_batch
                    })
                
            except Exception as e:
                logger.error(f"批次 {self.progress.current_batch} 处理失败: {e}")
                if config.enable_error_recovery:
                    self.failed_batches.append((self.progress.current_batch, batch, e))
                else:
                    raise
        
        # 重试失败的批次
        if config.retry_failed_batches and self.failed_batches:
            logger.info(f"重试 {len(self.failed_batches)} 个失败的批次")
            retry_results = await self._retry_failed_batches(process_rule, config)
            processed_docs.extend(retry_results.get("processed_docs", []))
            failed_docs.extend(retry_results.get("failed_docs", []))
        
        return {
            "success": True,
            "processed_count": len(processed_docs),
            "failed_count": len(failed_docs),
            "processed_docs": processed_docs,
            "failed_docs": failed_docs,
            "processing_time": self.progress.elapsed_time,
            "progress": self.progress
        }
    
    async def _parallel_process_documents(
        self,
        documents: List[Document],
        process_rule: Optional[ProcessRule],
        config: BatchConfig
    ) -> Dict[str, Any]:
        """并行处理文档"""
        processed_docs = []
        failed_docs = []
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(config.max_workers)
        
        async def process_batch_with_semaphore(batch_data):
            batch_index, batch = batch_data
            async with semaphore:
                try:
                    logger.info(f"并行处理批次 {batch_index + 1}/{self.progress.total_batches}")
                    
                    batch_results = []
                    for doc in batch:
                        try:
                            processed_doc = await self._process_single_document(doc, process_rule)
                            batch_results.append(processed_doc)
                        except Exception as e:
                            logger.error(f"处理文档失败: {e}")
                            failed_docs.append((doc, str(e)))
                    
                    return batch_results
                    
                except Exception as e:
                    logger.error(f"批次 {batch_index + 1} 处理失败: {e}")
                    if config.enable_error_recovery:
                        self.failed_batches.append((batch_index + 1, batch, e))
                    return []
        
        # 创建批次
        batches = []
        for i in range(0, len(documents), config.batch_size):
            batch = documents[i:i + config.batch_size]
            batches.append((i // config.batch_size, batch))
        
        # 并行处理所有批次
        tasks = [process_batch_with_semaphore(batch_data) for batch_data in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"批次处理异常: {result}")
            elif isinstance(result, list):
                processed_docs.extend(result)
        
        # 更新进度
        self.progress.processed_items = len(processed_docs)
        self.progress.failed_items = len(failed_docs)
        if config.enable_progress_tracking:
            self._update_progress()
        
        return {
            "success": True,
            "processed_count": len(processed_docs),
            "failed_count": len(failed_docs),
            "processed_docs": processed_docs,
            "failed_docs": failed_docs,
            "processing_time": self.progress.elapsed_time,
            "progress": self.progress
        }
    
    async def _adaptive_process_documents(
        self,
        documents: List[Document],
        process_rule: Optional[ProcessRule],
        config: BatchConfig
    ) -> Dict[str, Any]:
        """自适应处理文档"""
        # 根据文档数量和系统资源选择策略
        if len(documents) < 50:
            logger.info("文档数量较少，使用顺序处理")
            return await self._sequential_process_documents(documents, process_rule, config)
        elif len(documents) < 500:
            logger.info("文档数量适中，使用并行处理")
            return await self._parallel_process_documents(documents, process_rule, config)
        else:
            logger.info("文档数量较多，使用内存优化处理")
            return await self._memory_optimized_process_documents(documents, process_rule, config)
    
    async def _memory_optimized_process_documents(
        self,
        documents: List[Document],
        process_rule: Optional[ProcessRule],
        config: BatchConfig
    ) -> Dict[str, Any]:
        """内存优化处理文档"""
        # 使用较小的批次大小以减少内存使用
        optimized_config = BatchConfig(
            strategy=BatchStrategy.SEQUENTIAL,
            batch_size=min(config.batch_size, 20),  # 减小批次大小
            **{k: v for k, v in config.__dict__.items() if k not in ['strategy', 'batch_size']}
        )
        
        logger.info(f"内存优化模式：批次大小调整为 {optimized_config.batch_size}")
        return await self._sequential_process_documents(documents, process_rule, optimized_config)
    
    async def _process_single_document(
        self,
        document: Document,
        process_rule: Optional[ProcessRule]
    ) -> Document:
        """处理单个文档"""
        try:
            # 使用索引处理器处理文档
            # 这里简化处理，实际应该调用完整的处理流程
            processed_doc = document  # 占位符，实际需要调用处理逻辑
            return processed_doc
        except Exception as e:
            logger.error(f"处理单个文档失败: {e}")
            raise
    
    async def _retry_failed_batches(
        self,
        process_rule: Optional[ProcessRule],
        config: BatchConfig
    ) -> Dict[str, Any]:
        """重试失败的批次"""
        processed_docs = []
        failed_docs = []
        
        for batch_index, batch, original_error in self.failed_batches:
            for retry_attempt in range(config.max_retries):
                try:
                    logger.info(f"重试批次 {batch_index}，尝试 {retry_attempt + 1}/{config.max_retries}")
                    
                    batch_results = []
                    for doc in batch:
                        try:
                            processed_doc = await self._process_single_document(doc, process_rule)
                            batch_results.append(processed_doc)
                        except Exception as e:
                            failed_docs.append((doc, str(e)))
                    
                    processed_docs.extend(batch_results)
                    break  # 成功处理，跳出重试循环
                    
                except Exception as e:
                    logger.warning(f"批次 {batch_index} 重试 {retry_attempt + 1} 失败: {e}")
                    if retry_attempt == config.max_retries - 1:
                        # 最后一次重试也失败了
                        for doc in batch:
                            failed_docs.append((doc, f"重试失败: {str(e)}"))
        
        return {
            "processed_docs": processed_docs,
            "failed_docs": failed_docs
        }
    
    async def _save_checkpoint(self, checkpoint_name: str, data: Dict[str, Any]):
        """保存检查点"""
        self.checkpoints[checkpoint_name] = {
            "timestamp": time.time(),
            "data": data
        }
        logger.info(f"保存检查点: {checkpoint_name}")
    
    async def batch_create_embeddings(
        self,
        texts: List[str],
        config: BatchConfig = None
    ) -> List[List[float]]:
        """批量创建嵌入向量"""
        if config is None:
            config = BatchConfig()

        logger.info(f"开始批量创建 {len(texts)} 个文本的嵌入向量")

        try:
            # 使用嵌入模型的批量处理功能
            embeddings = self.embedding_model.embed_documents(texts)
            logger.info(f"成功创建 {len(embeddings)} 个嵌入向量")
            return embeddings

        except Exception as e:
            logger.error(f"批量创建嵌入向量失败: {e}")
            raise

    async def batch_index_documents(
        self,
        documents: List[Document],
        config: BatchConfig = None
    ) -> Dict[str, Any]:
        """批量索引文档到向量存储"""
        if config is None:
            config = BatchConfig()

        # 初始化进度
        self.progress = BatchProgress(
            total_items=len(documents),
            total_batches=math.ceil(len(documents) / config.batch_size),
            start_time=time.time()
        )

        logger.info(f"开始批量索引 {len(documents)} 个文档到向量存储")

        try:
            indexed_count = 0
            failed_count = 0
            failed_docs = []

            for i in range(0, len(documents), config.batch_size):
                batch = documents[i:i + config.batch_size]
                self.progress.current_batch = i // config.batch_size + 1

                try:
                    logger.info(f"索引批次 {self.progress.current_batch}/{self.progress.total_batches}")

                    # 提取文本内容
                    texts = [doc.page_content for doc in batch]

                    # 批量创建嵌入向量
                    embeddings = await self.batch_create_embeddings(texts, config)

                    # 批量插入向量存储
                    self.vector_store.insert(batch, embeddings)

                    # 批量存储到文档存储
                    if self.document_store:
                        for doc in batch:
                            # 转换为DocumentSegment格式
                            segment = DocumentSegment(
                                index_node_id=doc.metadata.get("id", str(time.time())),
                                doc_id=doc.metadata.get("doc_id", ""),
                                page_content=doc.page_content,  # 使用正确的字段名
                                metadata=doc.metadata
                            )
                            await self.document_store.store_segment(segment)

                    indexed_count += len(batch)
                    self.progress.processed_items += len(batch)

                    # 更新进度
                    if config.enable_progress_tracking:
                        self._update_progress()

                except Exception as e:
                    logger.error(f"批次 {self.progress.current_batch} 索引失败: {e}")
                    failed_count += len(batch)
                    self.progress.failed_items += len(batch)
                    failed_docs.extend([(doc, str(e)) for doc in batch])

                    if not config.enable_error_recovery:
                        raise

            return {
                "success": True,
                "indexed_count": indexed_count,
                "failed_count": failed_count,
                "failed_docs": failed_docs,
                "processing_time": self.progress.elapsed_time,
                "progress": self.progress
            }

        except Exception as e:
            logger.error(f"批量索引失败: {e}")
            raise

    async def batch_retrieve(
        self,
        queries: List[str],
        config: BatchConfig = None,
        retrieval_config: Optional[RetrievalConfig] = None
    ) -> Dict[str, Any]:
        """批量检索"""
        if config is None:
            config = BatchConfig()
        if retrieval_config is None:
            retrieval_config = RetrievalConfig()

        logger.info(f"开始批量检索 {len(queries)} 个查询")

        try:
            if self.parallel_retriever:
                # 使用并行检索器
                parallel_config = ParallelConfig(
                    max_workers=config.max_workers,
                    timeout_seconds=config.timeout_seconds,
                    enable_caching=True
                )
                results = await self.parallel_retriever.parallel_retrieve(
                    queries, parallel_config, retrieval_config
                )
            elif self.enhanced_retriever:
                # 使用增强检索器的批量功能
                results = await self.enhanced_retriever.batch_retrieve(queries, retrieval_config)
            else:
                raise ValueError("没有可用的检索器")

            return {
                "success": True,
                "query_count": len(queries),
                "results": results,
                "processing_time": time.time() - time.time()  # 简化时间计算
            }

        except Exception as e:
            logger.error(f"批量检索失败: {e}")
            raise

    async def batch_delete_documents(
        self,
        doc_ids: List[str],
        config: BatchConfig = None
    ) -> Dict[str, Any]:
        """批量删除文档"""
        if config is None:
            config = BatchConfig()

        logger.info(f"开始批量删除 {len(doc_ids)} 个文档")

        try:
            deleted_count = 0
            failed_count = 0
            failed_ids = []

            # 从向量存储删除
            try:
                self.vector_store.delete(doc_ids)
                deleted_count += len(doc_ids)
                logger.info(f"从向量存储删除 {len(doc_ids)} 个文档")
            except Exception as e:
                logger.error(f"从向量存储删除失败: {e}")
                failed_count += len(doc_ids)
                failed_ids.extend(doc_ids)

            # 从文档存储删除
            if self.document_store:
                for doc_id in doc_ids:
                    try:
                        await self.document_store.delete_segment(doc_id)
                    except Exception as e:
                        logger.error(f"从文档存储删除文档 {doc_id} 失败: {e}")
                        if doc_id not in failed_ids:
                            failed_ids.append(doc_id)
                            failed_count += 1

            return {
                "success": failed_count == 0,
                "deleted_count": deleted_count,
                "failed_count": failed_count,
                "failed_ids": failed_ids
            }

        except Exception as e:
            logger.error(f"批量删除失败: {e}")
            raise

    async def batch_update_documents(
        self,
        documents: List[Document],
        config: BatchConfig = None
    ) -> Dict[str, Any]:
        """批量更新文档"""
        if config is None:
            config = BatchConfig()

        logger.info(f"开始批量更新 {len(documents)} 个文档")

        try:
            # 先删除旧文档
            doc_ids = [doc.metadata.get("id") or doc.metadata.get("doc_id") for doc in documents]
            delete_result = await self.batch_delete_documents(doc_ids, config)

            # 再索引新文档
            index_result = await self.batch_index_documents(documents, config)

            return {
                "success": delete_result["success"] and index_result["success"],
                "updated_count": index_result["indexed_count"],
                "failed_count": delete_result["failed_count"] + index_result["failed_count"],
                "delete_result": delete_result,
                "index_result": index_result
            }

        except Exception as e:
            logger.error(f"批量更新失败: {e}")
            raise

    def get_progress(self) -> BatchProgress:
        """获取当前进度"""
        return self.progress

    def get_failed_batches(self) -> List[Tuple[int, List[Any], Exception]]:
        """获取失败的批次"""
        return self.failed_batches

    def clear_failed_batches(self):
        """清空失败的批次记录"""
        self.failed_batches.clear()
        logger.info("已清空失败批次记录")

    def get_checkpoints(self) -> Dict[str, Any]:
        """获取检查点"""
        return self.checkpoints

    def clear_checkpoints(self):
        """清空检查点"""
        self.checkpoints.clear()
        logger.info("已清空检查点")
