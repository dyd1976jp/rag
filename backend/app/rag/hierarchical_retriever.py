"""
层次化检索服务

基于Dify的检索架构实现，支持高效的父子检索和聚合
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from .models import (
    HierarchicalDocumentSegment,
    HierarchicalChildChunk, 
    ParentChildRelationship
)
from ..db.mongodb import mongodb

logger = logging.getLogger(__name__)


class HierarchicalRetrievalService:
    """层次化检索服务
    
    实现Dify风格的父子检索机制：
    1. 向量搜索仅针对子块
    2. 通过segment_id获取父段落信息
    3. 按父段落聚合结果并计算综合分数
    """
    
    def __init__(self, vector_store=None, embedding_model=None):
        """初始化检索服务
        
        Args:
            vector_store: 向量存储服务
            embedding_model: 嵌入模型
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        logger.info("层次化检索服务初始化完成")
    
    async def retrieve_with_parent_context(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
        enable_parent_context: bool = True
    ) -> List[Dict[str, Any]]:
        """检索时返回子块+父段落上下文
        
        Args:
            query: 查询文本
            dataset_id: 数据集ID，None表示搜索所有数据集
            top_k: 返回结果数量
            score_threshold: 分数阈值，低于此分数的结果将被过滤
            enable_parent_context: 是否启用父段落上下文
            
        Returns:
            List[Dict[str, Any]]: 检索结果列表
        """
        try:
            logger.info(f"开始层次化检索: query='{query[:50]}...', dataset_id={dataset_id}, top_k={top_k}")
            
            # 1. 向量搜索（仅搜索子块）
            child_chunks_with_scores = await self._vector_search_child_chunks(
                query, dataset_id, top_k * 2  # 多取一些候选，用于聚合
            )
            
            if not child_chunks_with_scores:
                logger.info("向量搜索未找到相关子块")
                return []
            
            logger.info(f"向量搜索找到 {len(child_chunks_with_scores)} 个相关子块")
            
            # 2. 过滤低分结果
            if score_threshold > 0:
                filtered_chunks = [
                    (chunk, score) for chunk, score in child_chunks_with_scores
                    if score >= score_threshold
                ]
                logger.info(f"分数过滤后剩余 {len(filtered_chunks)} 个子块")
                child_chunks_with_scores = filtered_chunks
            
            if not child_chunks_with_scores:
                logger.info("分数过滤后无结果")
                return []
            
            # 3. 获取父段落信息并组装结果
            if enable_parent_context:
                retrieval_results = await self._assemble_parent_child_results(
                    child_chunks_with_scores
                )
                
                # 4. 按父段落聚合和排序
                aggregated_results = self._aggregate_by_parent_segment(
                    retrieval_results
                )
                
                # 5. 返回前top_k个结果
                final_results = aggregated_results[:top_k]
            else:
                # 如果不需要父段落上下文，直接返回子块结果
                final_results = []
                for chunk, score in child_chunks_with_scores[:top_k]:
                    result = {
                        "child_chunk": {
                            "id": chunk.get("id"),
                            "content": chunk.get("content", ""),
                            "position": chunk.get("position", 0),
                            "score": score
                        },
                        "parent_segment": None,
                        "combined_score": score
                    }
                    final_results.append(result)
            
            logger.info(f"层次化检索完成，返回 {len(final_results)} 个结果")
            return final_results
            
        except Exception as e:
            logger.error(f"层次化检索失败: {str(e)}", exc_info=True)
            return []
    
    async def _vector_search_child_chunks(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """向量搜索子块
        
        Args:
            query: 查询文本
            dataset_id: 数据集ID
            top_k: 返回数量
            
        Returns:
            List[Tuple[Dict[str, Any], float]]: (子块信息, 分数) 列表
        """
        try:
            if not self.vector_store or not self.embedding_model:
                logger.error("向量存储或嵌入模型未初始化")
                return []
            
            # 生成查询向量
            query_vector = self.embedding_model.embed_query(query)
            
            # 构建过滤条件（仅搜索子块）
            filter_expr = 'metadata["type"] == "child"'
            if dataset_id:
                filter_expr += f' && metadata["dataset_id"] == "{dataset_id}"'
            
            # 执行向量搜索
            search_results = self.vector_store.search_by_vector(
                query_vector=query_vector,
                top_k=top_k,
                filter_expr=filter_expr
            )
            
            # 转换搜索结果
            child_chunks_with_scores = []
            for result in search_results:
                # result是Document对象，不是字典
                metadata = result.metadata if hasattr(result, 'metadata') else {}
                content = result.page_content if hasattr(result, 'page_content') else ""
                
                chunk_info = {
                    "id": metadata.get("id"),
                    "segment_id": metadata.get("parent_id"),  # 使用parent_id作为segment_id
                    "document_id": metadata.get("document_id"),
                    "dataset_id": metadata.get("dataset_id"),
                    "content": content,
                    "position": metadata.get("position", 0),
                    "word_count": metadata.get("word_count", len(content))
                }
                score = metadata.get("score", 0.0)
                child_chunks_with_scores.append((chunk_info, score))
            
            logger.debug(f"向量搜索返回 {len(child_chunks_with_scores)} 个子块结果")
            return child_chunks_with_scores
            
        except Exception as e:
            logger.error(f"向量搜索子块失败: {str(e)}", exc_info=True)
            return []
    
    async def _assemble_parent_child_results(
        self,
        child_chunks_with_scores: List[Tuple[Dict[str, Any], float]]
    ) -> List[Dict[str, Any]]:
        """组装父子检索结果
        
        Args:
            child_chunks_with_scores: (子块信息, 分数) 列表
            
        Returns:
            List[Dict[str, Any]]: 包含父子信息的结果列表
        """
        try:
            # 提取所有唯一的segment_id
            segment_ids = list(set(
                chunk[0]["segment_id"] for chunk in child_chunks_with_scores
                if chunk[0].get("segment_id")
            ))
            
            if not segment_ids:
                logger.warning("未找到有效的segment_id")
                return []
            
            # 批量获取父段落信息（从Milvus获取，因为MongoDB为空）
            segments_dict = {}
            if self.vector_store and hasattr(self.vector_store, 'get_by_ids'):
                try:
                    # 从Milvus获取父文档
                    parent_docs = self.vector_store.get_by_ids(segment_ids)
                    for doc in parent_docs:
                        if doc.metadata.get("type") == "parent":
                            segments_dict[doc.metadata.get("id")] = {
                                "id": doc.metadata.get("id"),
                                "content": doc.page_content,
                                "position": doc.metadata.get("index", 0),
                                "word_count": len(doc.page_content),
                                "child_count": 0  # 暂时设为0，实际可以计算
                            }
                except Exception as e:
                    logger.warning(f"从Milvus获取父文档失败: {e}")
            
            logger.debug(f"获取到 {len(segments_dict)} 个父段落信息")
            
            # 组装结果
            results = []
            for chunk_info, score in child_chunks_with_scores:
                segment_id = chunk_info.get("segment_id")
                segment_info = segments_dict.get(segment_id)
                
                if segment_info:
                    # 更新父段落的命中次数
                    await self._update_segment_hit_count(segment_id)
                    
                    result = {
                        "child_chunk": {
                            "id": chunk_info.get("id"),
                            "content": chunk_info.get("content", ""),
                            "position": chunk_info.get("position", 0),
                            "word_count": chunk_info.get("word_count", 0),
                            "score": score
                        },
                        "parent_segment": {
                            "id": segment_info["id"],
                            "content": segment_info.get("content", ""),
                            "position": segment_info.get("position", 0),
                            "word_count": segment_info.get("word_count", 0),
                            "child_count": segment_info.get("child_count", 0)
                        },
                        "combined_score": score
                    }
                    results.append(result)
                else:
                    logger.warning(f"未找到segment_id={segment_id}的父段落信息")
            
            logger.debug(f"组装了 {len(results)} 个父子结果")
            return results
            
        except Exception as e:
            logger.error(f"组装父子结果失败: {str(e)}", exc_info=True)
            return []
    
    def _aggregate_by_parent_segment(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """按父段落聚合结果
        
        Args:
            results: 包含父子信息的结果列表
            
        Returns:
            List[Dict[str, Any]]: 聚合后的结果列表，按分数排序
        """
        try:
            # 按父段落分组
            segment_groups = defaultdict(list)
            for result in results:
                segment_id = result["parent_segment"]["id"]
                segment_groups[segment_id].append(result)
            
            # 聚合每个组
            aggregated = []
            for segment_id, group in segment_groups.items():
                # 使用最高分作为段落分数
                max_score = max(r["child_chunk"]["score"] for r in group)
                
                # 计算平均分数
                avg_score = sum(r["child_chunk"]["score"] for r in group) / len(group)
                
                # 收集该段落下的所有相关子块
                child_chunks = [r["child_chunk"] for r in group]
                parent_segment = group[0]["parent_segment"]
                
                # 按子块在父段落中的位置排序
                child_chunks.sort(key=lambda x: x.get("position", 0))
                
                aggregated_result = {
                    "parent_segment": parent_segment,
                    "child_chunks": child_chunks,
                    "max_child_score": max_score,
                    "avg_child_score": avg_score,
                    "relevant_child_count": len(child_chunks),
                    "combined_score": max_score  # 使用最高分作为综合分数
                }
                aggregated.append(aggregated_result)
            
            # 按综合分数排序
            aggregated.sort(key=lambda x: x["combined_score"], reverse=True)
            
            logger.debug(f"聚合了 {len(aggregated)} 个父段落结果")
            return aggregated
            
        except Exception as e:
            logger.error(f"聚合结果失败: {str(e)}", exc_info=True)
            return []
    
    async def _update_segment_hit_count(self, segment_id: str) -> None:
        """更新父段落的命中次数
        
        Args:
            segment_id: 父段落ID
        """
        # MongoDB为空，跳过命中次数更新
        # 如果需要统计，可以考虑在内存中或其他方式记录
        pass
    
    async def get_segment_children(
        self,
        segment_id: str
    ) -> List[Dict[str, Any]]:
        """获取父段落的所有子块
        
        Args:
            segment_id: 父段落ID
            
        Returns:
            List[Dict[str, Any]]: 子块列表，按位置排序
        """
        try:
            chunks_cursor = mongodb.db["child_chunks"].find(
                {"segment_id": segment_id}
            ).sort("position", 1)
            
            chunks = []
            async for chunk_doc in chunks_cursor:
                chunks.append(chunk_doc)
            
            logger.debug(f"获取父段落 {segment_id} 的 {len(chunks)} 个子块")
            return chunks
            
        except Exception as e:
            logger.error(f"获取子块失败: {str(e)}", exc_info=True)
            return []
    
    async def get_document_segments_summary(
        self,
        document_id: str
    ) -> Dict[str, Any]:
        """获取文档的段落摘要信息
        
        Args:
            document_id: 文档ID
            
        Returns:
            Dict[str, Any]: 段落摘要信息
        """
        try:
            # 获取父段落统计
            segments_count = await mongodb.db["document_segments"].count_documents(
                {"document_id": document_id}
            )
            
            # 获取子块统计
            chunks_count = await mongodb.db["child_chunks"].count_documents(
                {"document_id": document_id}
            )
            
            # 获取命中次数统计
            pipeline = [
                {"$match": {"document_id": document_id}},
                {"$group": {
                    "_id": None,
                    "total_hits": {"$sum": "$hit_count"},
                    "avg_hits": {"$avg": "$hit_count"},
                    "max_hits": {"$max": "$hit_count"}
                }}
            ]
            
            hit_stats = None
            async for result in mongodb.db["document_segments"].aggregate(pipeline):
                hit_stats = result
                break
            
            summary = {
                "document_id": document_id,
                "segments_count": segments_count,
                "chunks_count": chunks_count,
                "avg_chunks_per_segment": chunks_count / segments_count if segments_count > 0 else 0,
                "hit_statistics": hit_stats or {
                    "total_hits": 0,
                    "avg_hits": 0,
                    "max_hits": 0
                }
            }
            
            logger.debug(f"文档 {document_id} 的摘要: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"获取文档段落摘要失败: {str(e)}", exc_info=True)
            return {
                "document_id": document_id,
                "error": str(e)
            }


# 全局实例
hierarchical_retriever = HierarchicalRetrievalService()