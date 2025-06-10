import logging
import time
from typing import List, Dict, Any, Optional
from .document_processor import Document
from .vector_store import BaseVectorStore, MilvusVectorStore
from .embedding_model import EmbeddingModel
from .cache_service import CacheService
import numpy as np
from .custom_exceptions import (
    RetrievalError, VectorStoreError, EmbeddingError, 
    DocumentProcessError, RerankingError, CacheError
)
from .models import Document, DocumentSegment, ChildChunk
from .document_store import DocumentStore
from .constants import DEFAULT_COLLECTION_NAME

# 配置日志
logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(
        self,
        vector_store: BaseVectorStore,
        document_store: DocumentStore,
        embedding_model: EmbeddingModel,
        retrieval_config: Dict[str, Any] = None,
        cache_service: Optional[CacheService] = None
    ):
        self.vector_store = vector_store
        self.document_store = document_store
        self.embedding_model = embedding_model
        self.retrieval_config = retrieval_config or {
            "top_k": 3,
            "score_threshold": 0.0,
            "score_threshold_enabled": False,
            "max_retries": 3,
            "retry_interval": 5,
            "reranking_model": {
                "enabled": False,
                "model": "default"
            }
        }
        self.cache_service = cache_service
        
        # 重试配置
        self.max_retries = self.retrieval_config.get("max_retries", 3)
        self.retry_interval = self.retrieval_config.get("retry_interval", 5)
        
    def retrieve(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        use_cache: bool = True
    ) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            dataset_id: 数据集ID，如果指定则只检索该数据集的文档
            top_k: 返回的最大结果数量
            score_threshold: 分数阈值，低于此分数的结果将被过滤
            use_cache: 是否使用缓存
            
        Returns:
            相关文档列表
        """
        try:
            # 如果启用了缓存，尝试从缓存获取结果
            if use_cache and self.cache_service:
                try:
                    cached_results = self.cache_service.get_cached_results(query, dataset_id or "all")
                    if cached_results:
                        logger.info(f"查询缓存命中: {query}")
                        return cached_results
                except CacheError as cache_error:
                    logger.warning(f"缓存读取失败，将跳过缓存: {str(cache_error)}")
            
            # 获取配置参数
            top_k = top_k or self.retrieval_config.get("top_k", 3)
            score_threshold = score_threshold or self.retrieval_config.get("score_threshold", 0.0)
            
            # 确保集合已初始化
            if self.vector_store.collection is None:
                logger.info("检索前发现集合未初始化，正在初始化集合...")
                try:
                    dimension = self.embedding_model.get_dimension()
                    self.vector_store.create_collection(DEFAULT_COLLECTION_NAME, dimension)
                    logger.info(f"集合 {DEFAULT_COLLECTION_NAME} 初始化完成")
                except VectorStoreError as vs_error:
                    logger.error(f"初始化向量存储失败: {str(vs_error)}")
                    raise RetrievalError(f"初始化向量存储失败: {str(vs_error)}")
                except EmbeddingError as emb_error:
                    logger.error(f"获取嵌入维度失败: {str(emb_error)}")
                    raise RetrievalError(f"获取嵌入维度失败: {str(emb_error)}")
            
            # 生成查询向量（带重试）
            try:
                query_vector = self._retry_operation(
                    self.embedding_model.embed_query,
                    query,
                    error_type=EmbeddingError
                )
            except EmbeddingError as e:
                logger.error(f"生成查询向量失败: {str(e)}")
                raise RetrievalError(f"生成查询向量失败: {str(e)}")
            
            # 执行向量检索（带重试）
            try:
                results = self._retry_operation(
                    self.vector_store.search_by_vector,
                    query_vector,
                    error_type=VectorStoreError,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    dataset_id=dataset_id
                )
            except VectorStoreError as e:
                logger.error(f"执行向量检索失败: {str(e)}")
                raise RetrievalError(f"执行向量检索失败: {str(e)}")
            
            # 如果需要重排序
            if self.retrieval_config.get("reranking_model", {}).get("enabled", False):
                try:
                    results = self._rerank_results(query, results)
                except RerankingError as e:
                    logger.warning(f"重排序失败，使用原始结果: {str(e)}")
                    # 不抛出异常，使用原始结果
                except Exception as e:
                    logger.warning(f"重排序过程中出现未知错误，使用原始结果: {str(e)}")
                    # 不抛出异常，使用原始结果
                
            # 如果启用了缓存，缓存结果
            if use_cache and self.cache_service and results:
                try:
                    self.cache_service.cache_results(query, dataset_id or "all", results)
                except CacheError as cache_error:
                    logger.warning(f"缓存结果失败: {str(cache_error)}")
                    # 不抛出异常，缓存失败不应影响检索结果
                
            return results
            
        except RetrievalError:
            # 重新抛出已处理的检索错误
            raise
        except Exception as e:
            logger.error(f"检索过程中出现未处理的错误: {str(e)}")
            raise RetrievalError(f"检索失败: {str(e)}")
            
    def _retry_operation(self, operation, *args, error_type=Exception, **kwargs):
        """执行带重试的操作"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except error_type as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"操作失败 ({type(e).__name__}: {str(e)})，{self.retry_interval}秒后重试 ({attempt+1}/{self.max_retries})...")
                    time.sleep(self.retry_interval)
                else:
                    logger.error(f"操作在{self.max_retries}次尝试后失败: {str(e)}")
                    raise last_error
    
    def _rerank_results(self, query: str, results: List[Document]) -> List[Document]:
        """使用交叉编码器对检索结果进行重排序"""
        try:
            # 如果结果为空或只有一个结果，不需要重排序
            if not results or len(results) <= 1:
                return results
                
            # 简单实现：使用余弦相似度重新排序
            # 在实际应用中，可以使用更高级的重排序模型
            logger.info(f"对 {len(results)} 个检索结果进行重排序")
            
            # 计算查询和文档的相似度分数
            try:
                query_embedding = self._retry_operation(
                    self.embedding_model.embed_query,
                    query,
                    error_type=EmbeddingError
                )
            except EmbeddingError as e:
                logger.error(f"重排序过程中生成查询向量失败: {str(e)}")
                raise RerankingError(f"生成查询向量失败: {str(e)}")
            
            doc_embeddings = []
            for doc in results:
                try:
                    embedding = self._retry_operation(
                        self.embedding_model.embed_query,
                        doc.page_content,
                        error_type=EmbeddingError
                    )
                    doc_embeddings.append(embedding)
                except EmbeddingError as e:
                    logger.warning(f"为文档生成嵌入向量失败，跳过该文档: {str(e)}")
                    # 使用零向量作为占位符，后续排序时会排在最后
                    doc_embeddings.append([0.0] * len(query_embedding))
            
            # 计算余弦相似度
            similarities = []
            for doc_embedding in doc_embeddings:
                try:
                    # 避免除零错误
                    norm_query = np.linalg.norm(query_embedding)
                    norm_doc = np.linalg.norm(doc_embedding)
                    
                    if norm_query > 0 and norm_doc > 0:
                        similarity = np.dot(query_embedding, doc_embedding) / (norm_query * norm_doc)
                    else:
                        similarity = 0.0
                    similarities.append(similarity)
                except Exception as e:
                    logger.warning(f"计算相似度失败: {str(e)}")
                    similarities.append(0.0)
                
            # 根据相似度重新排序
            sorted_indices = np.argsort(similarities)[::-1]
            reranked_results = [results[i] for i in sorted_indices]
            
            # 更新文档的分数
            for doc, score in zip(reranked_results, [similarities[i] for i in sorted_indices]):
                doc.metadata["score"] = float(score)
                
            logger.info("重排序完成")
            return reranked_results
            
        except RerankingError:
            # 重新抛出已处理的重排序错误
            raise
        except Exception as e:
            logger.error(f"重排序过程中出现未知错误: {str(e)}")
            raise RerankingError(f"重排序失败: {str(e)}")
                    
    async def process_document(self, document: Document) -> Dict[str, Any]:
        """处理文档，包括分割、向量化和存储"""
        try:
            from .document_splitter import HierarchicalDocumentSplitter
            splitter = HierarchicalDocumentSplitter()
            
            # 1. 分割成父块
            segments = splitter.split_document(document)
            logger.info(f"文档分割完成，生成 {len(segments)} 个父块")
            
            # 2. 存储父块
            for segment in segments:
                # 存储父块
                await self.document_store.store_segment(segment)
                
                # 分割子块
                chunks = splitter.split_segment(segment)
                
                # 向量化子块
                chunk_contents = [chunk.content for chunk in chunks]
                vectors = self.embedding_model.embed_documents(chunk_contents)
                
                # 添加向量到子块
                for chunk, vector in zip(chunks, vectors):
                    chunk.vector = vector
                
                # 存储子块
                await self.document_store.store_chunks(chunks)
                
                # 存储子块向量
                self.vector_store.insert_chunks(chunks)
                
            return {
                "success": True,
                "message": f"文档处理成功，生成 {len(segments)} 个父块"
            }
            
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            return {
                "success": False,
                "message": f"文档处理失败: {str(e)}"
            }
            
    async def search(
        self,
        query: str,
        top_k: int = 3,
        include_segments: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索相关内容"""
        try:
            # 1. 向量化查询
            query_vector = self.embedding_model.embed_query(query)
            
            # 2. 搜索相似子块
            results = self.vector_store.search(query_vector, top_k)
            
            # 3. 获取父块信息（如果需要）
            if include_segments:
                for result in results:
                    segment_id = result["segment_id"]
                    segment = await self.document_store.get_segment(segment_id)
                    if segment:
                        result["segment"] = segment.dict()
                        
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise
            
    async def delete_document(self, doc_id: str):
        """删除文档及其所有分块"""
        try:
            # 查找所有相关的父块
            cursor = self.document_store.segments_collection.find(
                {"metadata.doc_id": doc_id}
            )
            
            async for segment in cursor:
                segment_id = segment["index_node_id"]
                # 删除父块及其子块
                await self.document_store.delete_segment(segment_id)
                # 删除向量存储中的子块
                self.vector_store.delete_by_segment_id(segment_id)
                
            logger.info(f"文档 {doc_id} 及其所有分块删除成功")
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise
    
    async def process_and_index_document(
        self, 
        document: Document, 
        collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> Dict[str, Any]:
        """
        处理单个文档并建立索引
        
        Args:
            document: 要处理的文档
            collection_name: 向量集合名称
            
        Returns:
            处理结果信息
        """
        try:
            # 获取嵌入向量维度
            dimension = self.embedding_model.get_dimension()
            
            # 确保集合存在
            self.vector_store.create_collection(collection_name, dimension)
            
            # 生成文档向量
            embeddings = self.embedding_model.embed_documents([document.page_content])
            
            # 插入到向量存储
            self.vector_store.insert([document], embeddings)
            
            return {
                "success": True,
                "doc_id": document.metadata.get("doc_id"),
                "message": "文档处理和索引成功"
            }
            
        except Exception as e:
            logger.error(f"文档处理和索引失败: {str(e)}")
            return {
                "success": False,
                "message": f"文档处理和索引失败: {str(e)}"
            }
            
    async def process_and_index_documents_batch(
        self, 
        documents: List[Document], 
        collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> Dict[str, Any]:
        """
        批量处理文档并建立索引
        
        Args:
            documents: 文档列表
            collection_name: 向量集合名称
            
        Returns:
            处理结果信息
        """
        if not documents:
            return {
                "success": False,
                "message": "文档列表为空，无需处理"
            }
            
        try:
            start_time = time.time()
            
            # 获取嵌入向量维度
            dimension = self.embedding_model.get_dimension()
            
            # 确保集合存在
            self.vector_store.create_collection(collection_name, dimension)
            
            # 收集所有文档内容
            doc_contents = [doc.page_content for doc in documents]
            
            # 批量生成文档向量
            logger.info(f"开始为 {len(documents)} 个文档生成嵌入向量")
            embeddings = self.embedding_model.embed_documents(doc_contents)
            embedding_time = time.time()
            logger.info(f"嵌入向量生成完成，耗时 {embedding_time - start_time:.2f} 秒")
            
            # 批量插入到向量存储
            logger.info(f"开始批量插入 {len(documents)} 个文档到向量存储")
            self.vector_store.insert(documents, embeddings)
            insert_time = time.time()
            logger.info(f"向量插入完成，耗时 {insert_time - embedding_time:.2f} 秒")
            
            total_time = time.time() - start_time
            logger.info(f"批量处理 {len(documents)} 个文档完成，总耗时 {total_time:.2f} 秒")
            
            # 收集处理的文档ID
            doc_ids = [doc.metadata.get("doc_id") for doc in documents]
            
            return {
                "success": True,
                "doc_ids": doc_ids,
                "count": len(documents),
                "processing_time": total_time,
                "message": f"批量处理和索引 {len(documents)} 个文档成功"
            }
            
        except Exception as e:
            logger.error(f"批量文档处理和索引失败: {str(e)}")
            return {
                "success": False,
                "message": f"批量文档处理和索引失败: {str(e)}"
            }
    
    def retrieve_with_parent(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        检索文档并包含其父文档
        
        Args:
            query: 查询文本
            dataset_id: 数据集ID，如果指定则只检索该数据集的文档
            top_k: 返回的最大结果数量
            use_cache: 是否使用缓存
            
        Returns:
            包含子文档和父文档的结果列表
        """
        try:
            # 获取子文档
            child_docs = self.retrieve(query, dataset_id, top_k, use_cache=use_cache)
            
            # 组织结果
            results = []
            for doc in child_docs:
                parent_id = doc.metadata.get("parent_id")
                if parent_id:
                    # 获取父文档（带重试）
                    parent_doc = self._retry_operation(
                        self.vector_store.get_by_id,
                        parent_id,
                        error_type=VectorStoreError
                    )
                    if parent_doc:
                        results.append({
                            "child_document": doc,
                            "parent_document": parent_doc,
                            "score": doc.metadata.get("score", 0.0)
                        })
                else:
                    # 如果没有父文档ID，则当前文档作为独立文档返回
                    results.append({
                        "child_document": doc,
                        "parent_document": None,
                        "score": doc.metadata.get("score", 0.0)
                    })
                        
            return results
            
        except Exception as e:
            logger.error(f"检索父子文档过程中出错: {str(e)}")
            raise RetrievalError(f"父子文档检索失败: {str(e)}") 