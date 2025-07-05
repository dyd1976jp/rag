"""
RAG流程管道组件

实现完整的RAG流程编排，将各个组件串联成完整的处理流程。
实现IRagPipeline接口，提供统一的RAG流程管理。
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Union, Optional
from datetime import datetime

from app.rag.interfaces import (
    BaseRagPipeline, 
    IDocumentLoader, 
    ITextSplitter, 
    IEmbedder, 
    IRetriever, 
    IGenerator,
    GenerationResult
)

logger = logging.getLogger(__name__)

class RagPipeline(BaseRagPipeline):
    """RAG流程管道实现"""
    
    def __init__(
        self,
        loader: IDocumentLoader,
        splitter: ITextSplitter,
        embedder: IEmbedder,
        retriever: IRetriever,
        generator: IGenerator
    ):
        """
        初始化RAG流程管道
        
        Args:
            loader: 文档加载器
            splitter: 文本分割器
            embedder: 向量嵌入器
            retriever: 文档检索器
            generator: 答案生成器
        """
        self.loader = loader
        self.splitter = splitter
        self.embedder = embedder
        self.retriever = retriever
        self.generator = generator
        
        # 流程统计
        self.stats = {
            "documents_processed": 0,
            "queries_processed": 0,
            "total_chunks_created": 0,
            "average_processing_time": 0.0
        }
    
    async def process_document(
        self,
        file_path: Union[str, Path],
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理文档的完整流程
        
        Args:
            file_path: 文档路径
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        start_time = datetime.now()
        process_id = str(uuid.uuid4())
        
        try:
            logger.info(f"开始处理文档: {file_path} (用户: {user_id}, 流程ID: {process_id})")
            
            # 1. 加载文档
            logger.info("步骤 1: 加载文档")
            document = await self.loader.load_document(file_path)
            
            # 添加用户信息到元数据
            document.metadata.update({
                "user_id": user_id,
                "process_id": process_id,
                "processed_at": datetime.now().isoformat()
            })
            
            # 2. 分割文档
            logger.info("步骤 2: 分割文档")
            
            # 应用自定义分割参数
            if kwargs:
                self.splitter.configure(**kwargs)
            
            chunks = await self.splitter.split_document(document)
            
            if not chunks:
                return {
                    "success": False,
                    "message": "文档分割后没有生成有效的文本块",
                    "process_id": process_id
                }
            
            # 3. 向量化文档块
            logger.info(f"步骤 3: 向量化 {len(chunks)} 个文档块")
            
            # 批量向量化
            chunk_texts = [chunk.content for chunk in chunks]
            vectors = await self.embedder.embed_documents(chunk_texts)
            
            # 将向量添加到文档块
            for chunk, vector in zip(chunks, vectors):
                chunk.vector = vector
                chunk.metadata.update({
                    "user_id": user_id,
                    "process_id": process_id
                })
            
            # 4. 存储到检索索引
            logger.info("步骤 4: 存储到检索索引")
            success = await self.retriever.add_documents(chunks)
            
            if not success:
                return {
                    "success": False,
                    "message": "文档存储到检索索引失败",
                    "process_id": process_id
                }
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 更新统计信息
            self._update_processing_stats(processing_time, len(chunks))
            
            result = {
                "success": True,
                "message": "文档处理完成",
                "process_id": process_id,
                "document_info": {
                    "doc_id": document.doc_id,
                    "file_name": document.metadata.get("file_name"),
                    "file_size": document.metadata.get("file_size"),
                    "content_length": len(document.content)
                },
                "processing_info": {
                    "chunks_created": len(chunks),
                    "processing_time": processing_time,
                    "average_chunk_size": sum(len(chunk.content) for chunk in chunks) // len(chunks)
                }
            }
            
            logger.info(f"文档处理完成: {file_path} (耗时: {processing_time:.2f}秒)")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"文档处理失败: {e} (耗时: {processing_time:.2f}秒)")
            
            return {
                "success": False,
                "message": f"文档处理失败: {str(e)}",
                "process_id": process_id,
                "error": str(e)
            }
    
    async def query(
        self,
        question: str,
        user_id: str,
        **kwargs
    ) -> GenerationResult:
        """
        查询的完整流程
        
        Args:
            question: 用户问题
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            GenerationResult: 查询结果
        """
        start_time = datetime.now()
        query_id = str(uuid.uuid4())
        
        try:
            logger.info(f"开始处理查询: {question[:50]}... (用户: {user_id}, 查询ID: {query_id})")
            
            # 1. 检索相关文档
            logger.info("步骤 1: 检索相关文档")
            
            # 构建检索过滤条件
            filters = {"user_id": user_id}
            if "dataset_id" in kwargs:
                filters["dataset_id"] = kwargs["dataset_id"]
            
            top_k = kwargs.get("top_k", 5)
            retrieval_results = await self.retriever.retrieve(
                query=question,
                top_k=top_k,
                filters=filters
            )
            
            if not retrieval_results:
                logger.warning("没有检索到相关文档")
                return GenerationResult(
                    answer="抱歉，我没有找到与您的问题相关的文档内容。请确保已上传相关文档或尝试重新表述您的问题。",
                    sources=[],
                    metadata={
                        "query_id": query_id,
                        "user_id": user_id,
                        "retrieval_count": 0,
                        "processing_time": (datetime.now() - start_time).total_seconds()
                    }
                )
            
            # 2. 生成答案
            logger.info(f"步骤 2: 基于 {len(retrieval_results)} 个文档片段生成答案")
            
            generation_result = await self.generator.generate(
                query=question,
                context=retrieval_results,
                **kwargs
            )
            
            # 添加查询元数据
            generation_result.metadata.update({
                "query_id": query_id,
                "user_id": user_id,
                "retrieval_count": len(retrieval_results),
                "processing_time": (datetime.now() - start_time).total_seconds()
            })
            
            # 更新统计信息
            self.stats["queries_processed"] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"查询处理完成 (耗时: {processing_time:.2f}秒)")
            
            return generation_result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"查询处理失败: {e} (耗时: {processing_time:.2f}秒)")
            
            return GenerationResult(
                answer="抱歉，处理您的问题时出现错误，请稍后重试。",
                sources=[],
                metadata={
                    "query_id": query_id,
                    "user_id": user_id,
                    "error": str(e),
                    "processing_time": processing_time
                }
            )
    
    def _update_processing_stats(self, processing_time: float, chunks_count: int):
        """更新处理统计信息"""
        self.stats["documents_processed"] += 1
        self.stats["total_chunks_created"] += chunks_count
        
        # 计算平均处理时间
        total_docs = self.stats["documents_processed"]
        current_avg = self.stats["average_processing_time"]
        self.stats["average_processing_time"] = (
            (current_avg * (total_docs - 1) + processing_time) / total_docs
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """
        健康检查所有组件
        
        Returns:
            Dict[str, bool]: 各组件健康状态
        """
        health_status = {}
        
        try:
            # 检查嵌入器
            health_status["embedder"] = await self.embedder.health_check()
        except Exception:
            health_status["embedder"] = False
        
        try:
            # 检查生成器
            health_status["generator"] = await self.generator.health_check()
        except Exception:
            health_status["generator"] = False
        
        try:
            # 检查检索器（简单检查）
            stats = await self.retriever.get_collection_stats()
            health_status["retriever"] = bool(stats)
        except Exception:
            health_status["retriever"] = False
        
        # 检查加载器和分割器（无需异步检查）
        health_status["loader"] = True
        health_status["splitter"] = True
        
        return health_status
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """获取流程统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "documents_processed": 0,
            "queries_processed": 0,
            "total_chunks_created": 0,
            "average_processing_time": 0.0
        }
