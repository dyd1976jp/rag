"""
高级重排序模块
支持多种重排序策略和算法
"""

import logging
import asyncio
import time
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

from .enhanced_retriever import RetrievalResult, RerankingMethod
from .models import Document

logger = logging.getLogger(__name__)


class AdvancedRerankingMethod(str, Enum):
    """高级重排序方法枚举"""
    RECIPROCAL_RANK_FUSION = "rrf"      # 倒数排名融合
    WEIGHTED_SCORE_FUSION = "wsf"       # 加权分数融合
    LEARNING_TO_RANK = "ltr"            # 学习排序
    DIVERSITY_RERANKING = "diversity"   # 多样性重排序
    TEMPORAL_DECAY = "temporal"         # 时间衰减排序
    SEMANTIC_CLUSTERING = "clustering"  # 语义聚类排序
    CROSS_ENCODER = "cross_encoder"     # 交叉编码器重排序


@dataclass
class RerankingConfig:
    """重排序配置"""
    method: AdvancedRerankingMethod = AdvancedRerankingMethod.RECIPROCAL_RANK_FUSION
    
    # RRF配置
    rrf_k: float = 60.0  # RRF参数k
    
    # 加权融合配置
    score_weights: Dict[str, float] = None
    
    # 多样性配置
    diversity_lambda: float = 0.5  # 多样性权重
    max_diversity_results: int = 10
    
    # 时间衰减配置
    time_decay_factor: float = 0.1
    time_window_days: int = 30
    
    # 聚类配置
    cluster_threshold: float = 0.8
    max_clusters: int = 5
    
    # 通用配置
    top_k: int = 10
    enable_parallel: bool = True


class BaseAdvancedReranker(ABC):
    """高级重排序器基类"""
    
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        config: RerankingConfig
    ) -> List[RetrievalResult]:
        """执行重排序"""
        pass


class ReciprocalRankFusionReranker(BaseAdvancedReranker):
    """倒数排名融合重排序器"""
    
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        config: RerankingConfig
    ) -> List[RetrievalResult]:
        """使用RRF算法重排序"""
        if not results:
            return results
        
        try:
            logger.debug(f"执行RRF重排序，结果数量: {len(results)}")
            
            # 按不同方法分组结果
            method_results = defaultdict(list)
            for result in results:
                method_results[result.method].append(result)
            
            # 为每个方法的结果计算排名
            method_rankings = {}
            for method, method_res in method_results.items():
                # 按分数排序
                sorted_results = sorted(method_res, key=lambda x: x.score, reverse=True)
                rankings = {id(res): rank + 1 for rank, res in enumerate(sorted_results)}
                method_rankings[method] = rankings
            
            # 计算RRF分数
            rrf_scores = {}
            for result in results:
                rrf_score = 0.0
                result_id = id(result)
                
                for method, rankings in method_rankings.items():
                    if result_id in rankings:
                        rank = rankings[result_id]
                        rrf_score += 1.0 / (config.rrf_k + rank)
                
                rrf_scores[result_id] = rrf_score
                result.rerank_score = rrf_score
            
            # 按RRF分数排序
            reranked_results = sorted(results, key=lambda x: rrf_scores[id(x)], reverse=True)
            
            logger.info(f"RRF重排序完成，返回 {len(reranked_results)} 个结果")
            return reranked_results[:config.top_k]
            
        except Exception as e:
            logger.error(f"RRF重排序失败: {str(e)}")
            return results


class WeightedScoreFusionReranker(BaseAdvancedReranker):
    """加权分数融合重排序器"""
    
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        config: RerankingConfig
    ) -> List[RetrievalResult]:
        """使用加权分数融合重排序"""
        if not results:
            return results
        
        try:
            logger.debug(f"执行加权分数融合重排序，结果数量: {len(results)}")
            
            # 默认权重
            if config.score_weights is None:
                config.score_weights = {
                    "vector_score": 0.4,
                    "keyword_score": 0.3,
                    "quality_score": 0.2,
                    "time_score": 0.1
                }
            
            # 计算加权分数
            for result in results:
                weighted_score = 0.0
                
                # 向量分数
                if result.vector_score is not None:
                    weighted_score += config.score_weights.get("vector_score", 0) * result.vector_score
                
                # 关键词分数
                if result.keyword_score is not None:
                    weighted_score += config.score_weights.get("keyword_score", 0) * result.keyword_score
                
                # 质量分数（需要计算）
                quality_score = self._calculate_quality_score(result)
                weighted_score += config.score_weights.get("quality_score", 0) * quality_score
                
                # 时间分数（需要计算）
                time_score = self._calculate_time_score(result)
                weighted_score += config.score_weights.get("time_score", 0) * time_score
                
                result.rerank_score = weighted_score
            
            # 按加权分数排序
            reranked_results = sorted(results, key=lambda x: x.rerank_score or 0, reverse=True)
            
            logger.info(f"加权分数融合重排序完成，返回 {len(reranked_results)} 个结果")
            return reranked_results[:config.top_k]
            
        except Exception as e:
            logger.error(f"加权分数融合重排序失败: {str(e)}")
            return results
    
    def _calculate_quality_score(self, result: RetrievalResult) -> float:
        """计算质量分数"""
        content = result.document.page_content
        
        # 基于长度的质量评估
        length_score = min(1.0, len(content) / 1000)
        
        # 基于结构的质量评估
        structure_score = 0.5
        if "。" in content or "." in content:  # 有句号
            structure_score += 0.2
        if "\n" in content:  # 有换行
            structure_score += 0.1
        if len(content.split()) > 10:  # 词数足够
            structure_score += 0.2
        
        return (length_score + min(1.0, structure_score)) / 2
    
    def _calculate_time_score(self, result: RetrievalResult) -> float:
        """计算时间分数"""
        timestamp = result.document.metadata.get("timestamp")
        if not timestamp:
            return 0.5
        
        try:
            current_time = time.time()
            doc_time = float(timestamp)
            time_diff_days = (current_time - doc_time) / (24 * 3600)
            
            # 时间衰减函数
            return max(0.1, math.exp(-time_diff_days / 30))
        except (ValueError, TypeError):
            return 0.5


class DiversityReranker(BaseAdvancedReranker):
    """多样性重排序器"""
    
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        config: RerankingConfig
    ) -> List[RetrievalResult]:
        """使用多样性算法重排序"""
        if not results:
            return results
        
        try:
            logger.debug(f"执行多样性重排序，结果数量: {len(results)}")
            
            # 计算文档间的相似度矩阵
            similarity_matrix = self._calculate_similarity_matrix(results)
            
            # 使用贪心算法选择多样化结果
            selected_results = []
            remaining_results = results.copy()
            
            # 首先选择分数最高的结果
            if remaining_results:
                best_result = max(remaining_results, key=lambda x: x.score)
                best_result.rerank_score = best_result.score  # 设置重排序分数
                selected_results.append(best_result)
                remaining_results.remove(best_result)
            
            # 迭代选择剩余结果
            while remaining_results and len(selected_results) < config.max_diversity_results:
                best_candidate = None
                best_score = -1
                
                for candidate in remaining_results:
                    # 计算多样性分数
                    relevance_score = candidate.score
                    diversity_score = self._calculate_diversity_score(
                        candidate, selected_results, similarity_matrix, results
                    )
                    
                    # 组合分数
                    combined_score = (
                        (1 - config.diversity_lambda) * relevance_score +
                        config.diversity_lambda * diversity_score
                    )
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_candidate = candidate
                
                if best_candidate:
                    best_candidate.rerank_score = best_score
                    selected_results.append(best_candidate)
                    remaining_results.remove(best_candidate)
            
            logger.info(f"多样性重排序完成，返回 {len(selected_results)} 个结果")
            return selected_results[:config.top_k]
            
        except Exception as e:
            logger.error(f"多样性重排序失败: {str(e)}")
            return results[:config.top_k]
    
    def _calculate_similarity_matrix(self, results: List[RetrievalResult]) -> Dict[Tuple[int, int], float]:
        """计算文档间相似度矩阵"""
        similarity_matrix = {}
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results):
                if i != j:
                    similarity = self._calculate_text_similarity(
                        result1.document.page_content,
                        result2.document.page_content
                    )
                    similarity_matrix[(i, j)] = similarity
        
        return similarity_matrix
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版本）"""
        # 简单的词汇重叠相似度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_diversity_score(
        self,
        candidate: RetrievalResult,
        selected_results: List[RetrievalResult],
        similarity_matrix: Dict[Tuple[int, int], float],
        all_results: List[RetrievalResult]
    ) -> float:
        """计算多样性分数"""
        if not selected_results:
            return 1.0
        
        candidate_idx = all_results.index(candidate)
        max_similarity = 0.0
        
        for selected in selected_results:
            selected_idx = all_results.index(selected)
            similarity = similarity_matrix.get((candidate_idx, selected_idx), 0.0)
            max_similarity = max(max_similarity, similarity)
        
        # 多样性分数 = 1 - 最大相似度
        return 1.0 - max_similarity


class AdvancedRerankerService:
    """高级重排序服务"""
    
    def __init__(self):
        self.rerankers = {
            AdvancedRerankingMethod.RECIPROCAL_RANK_FUSION: ReciprocalRankFusionReranker(),
            AdvancedRerankingMethod.WEIGHTED_SCORE_FUSION: WeightedScoreFusionReranker(),
            AdvancedRerankingMethod.DIVERSITY_RERANKING: DiversityReranker(),
        }
    
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        config: RerankingConfig = None
    ) -> List[RetrievalResult]:
        """执行高级重排序"""
        if config is None:
            config = RerankingConfig()
        
        if not results:
            return results
        
        try:
            logger.info(f"开始高级重排序，方法: {config.method}, 结果数量: {len(results)}")
            start_time = time.time()
            
            # 选择重排序器
            reranker = self.rerankers.get(config.method)
            if not reranker:
                logger.warning(f"未找到重排序器: {config.method}，使用默认排序")
                return results[:config.top_k]
            
            # 执行重排序
            reranked_results = await reranker.rerank(query, results, config)
            
            elapsed_time = time.time() - start_time
            logger.info(f"高级重排序完成，耗时: {elapsed_time:.3f}s, 返回 {len(reranked_results)} 个结果")
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"高级重排序失败: {str(e)}")
            return results[:config.top_k]
    
    async def multi_stage_rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        configs: List[RerankingConfig]
    ) -> List[RetrievalResult]:
        """多阶段重排序"""
        current_results = results
        
        for i, config in enumerate(configs):
            logger.info(f"执行第 {i+1} 阶段重排序: {config.method}")
            current_results = await self.rerank(query, current_results, config)
        
        return current_results
