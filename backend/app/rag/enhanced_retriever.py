"""
增强的检索器模块
支持多种检索方法：向量检索、关键词检索、混合检索等
"""

import logging
import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
import numpy as np
import re
from collections import Counter
import math

from .models import Document
from .embedding_model import EmbeddingModel
from .vector_store import MilvusVectorStore

logger = logging.getLogger(__name__)


class RetrievalMethod(str, Enum):
    """检索方法枚举"""
    VECTOR = "vector"           # 纯向量检索
    KEYWORD = "keyword"         # 关键词检索
    HYBRID = "hybrid"           # 混合检索
    SEMANTIC = "semantic"       # 语义检索
    FUZZY = "fuzzy"            # 模糊检索


class RerankingMethod(str, Enum):
    """重排序方法枚举"""
    RELEVANCE = "relevance"     # 相关性排序
    TIME = "time"              # 时间排序
    QUALITY = "quality"        # 质量排序
    HYBRID_SCORE = "hybrid_score"  # 混合分数排序


@dataclass
class RetrievalConfig:
    """检索配置"""
    method: RetrievalMethod = RetrievalMethod.VECTOR
    top_k: int = 10
    score_threshold: float = 0.0
    
    # 向量检索配置
    vector_weight: float = 0.7
    
    # 关键词检索配置
    keyword_weight: float = 0.3
    min_keyword_length: int = 2
    max_keywords: int = 10
    
    # 混合检索配置
    hybrid_alpha: float = 0.5  # 向量检索权重
    
    # 重排序配置
    enable_reranking: bool = True
    reranking_method: RerankingMethod = RerankingMethod.HYBRID_SCORE
    reranking_top_k: int = 50  # 重排序前的候选数量
    
    # 性能配置
    enable_parallel: bool = True
    timeout_seconds: float = 30.0


@dataclass
class RetrievalResult:
    """检索结果"""
    document: Document
    score: float
    method: RetrievalMethod
    metadata: Dict[str, Any]
    
    # 详细分数信息
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    rerank_score: Optional[float] = None


class BaseRetriever(ABC):
    """检索器基类"""
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        config: RetrievalConfig
    ) -> List[RetrievalResult]:
        """执行检索"""
        pass


class VectorRetriever(BaseRetriever):
    """向量检索器"""
    
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: MilvusVectorStore
    ):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    async def retrieve(
        self,
        query: str,
        config: RetrievalConfig
    ) -> List[RetrievalResult]:
        """执行向量检索"""
        try:
            logger.debug(f"执行向量检索: {query[:50]}...")
            
            # 生成查询向量
            query_vector = self.embedding_model.embed_query(query)
            
            # 执行向量搜索
            results = self.vector_store.search_by_vector(
                query_vector=query_vector,
                top_k=config.top_k,
                score_threshold=config.score_threshold
            )
            
            # 转换结果格式
            retrieval_results = []
            for doc in results:
                score = doc.metadata.get("score", 0.0)
                result = RetrievalResult(
                    document=doc,
                    score=score,
                    method=RetrievalMethod.VECTOR,
                    metadata={"retrieval_time": time.time()},
                    vector_score=score
                )
                retrieval_results.append(result)
            
            logger.info(f"向量检索完成，返回 {len(retrieval_results)} 个结果")
            return retrieval_results
            
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []


class KeywordRetriever(BaseRetriever):
    """关键词检索器"""
    
    def __init__(self, vector_store: MilvusVectorStore):
        self.vector_store = vector_store
        # 停用词列表
        self.stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"
        }
    
    def _extract_keywords(self, text: str, config: RetrievalConfig) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（实际项目中可以使用jieba等工具进行中文分词）

        # 移除标点符号，但保留中文字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)

        # 中文文本处理：提取中文词汇和英文单词
        keywords = []

        # 提取中文词汇（简单的2-4字词组合）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for chars in chinese_chars:
            if len(chars) >= 2:
                # 生成2-4字的词组
                for i in range(len(chars)):
                    for length in [2, 3, 4]:
                        if i + length <= len(chars):
                            word = chars[i:i+length]
                            if word not in self.stop_words:
                                keywords.append(word)

        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        for word in english_words:
            if len(word) >= config.min_keyword_length and word not in self.stop_words:
                keywords.append(word)

        # 统计词频并返回最频繁的关键词
        word_counts = Counter(keywords)
        top_keywords = [word for word, _ in word_counts.most_common(config.max_keywords)]

        return top_keywords
    
    def _calculate_keyword_score(self, query_keywords: List[str], doc_content: str) -> float:
        """计算关键词匹配分数"""
        if not query_keywords:
            return 0.0
        
        doc_content_lower = doc_content.lower()
        matches = 0
        total_keywords = len(query_keywords)
        
        for keyword in query_keywords:
            if keyword.lower() in doc_content_lower:
                matches += 1
        
        return matches / total_keywords if total_keywords > 0 else 0.0
    
    async def retrieve(
        self,
        query: str,
        config: RetrievalConfig
    ) -> List[RetrievalResult]:
        """执行关键词检索"""
        try:
            logger.debug(f"执行关键词检索: {query[:50]}...")
            
            # 提取查询关键词
            keywords = self._extract_keywords(query, config)
            if not keywords:
                logger.warning("未提取到有效关键词")
                return []
            
            logger.debug(f"提取到关键词: {keywords}")
            
            # 获取所有文档（实际项目中应该有更高效的关键词索引）
            # 这里简化处理，实际应该使用全文搜索引擎如Elasticsearch
            all_docs = self.vector_store.get_all_documents(limit=1000)
            
            # 计算关键词匹配分数
            scored_results = []
            for doc in all_docs:
                keyword_score = self._calculate_keyword_score(keywords, doc.page_content)
                if keyword_score > 0:
                    result = RetrievalResult(
                        document=doc,
                        score=keyword_score,
                        method=RetrievalMethod.KEYWORD,
                        metadata={"keywords": keywords, "retrieval_time": time.time()},
                        keyword_score=keyword_score
                    )
                    scored_results.append(result)
            
            # 按分数排序并返回top_k
            scored_results.sort(key=lambda x: x.score, reverse=True)
            results = scored_results[:config.top_k]
            
            logger.info(f"关键词检索完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"关键词检索失败: {str(e)}")
            return []


class HybridRetriever(BaseRetriever):
    """混合检索器"""
    
    def __init__(
        self,
        vector_retriever: VectorRetriever,
        keyword_retriever: KeywordRetriever
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
    
    def _merge_results(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        config: RetrievalConfig
    ) -> List[RetrievalResult]:
        """合并向量检索和关键词检索结果"""
        # 创建文档ID到结果的映射
        doc_map = {}
        
        # 处理向量检索结果
        for result in vector_results:
            doc_id = result.document.metadata.get("id", "")
            if doc_id:
                doc_map[doc_id] = result
        
        # 处理关键词检索结果
        for result in keyword_results:
            doc_id = result.document.metadata.get("id", "")
            if doc_id:
                if doc_id in doc_map:
                    # 合并分数
                    existing = doc_map[doc_id]
                    hybrid_score = (
                        config.hybrid_alpha * (existing.vector_score or 0) +
                        (1 - config.hybrid_alpha) * (result.keyword_score or 0)
                    )
                    existing.score = hybrid_score
                    existing.method = RetrievalMethod.HYBRID
                    existing.keyword_score = result.keyword_score
                    existing.metadata.update(result.metadata)
                else:
                    # 只有关键词匹配的结果
                    result.score = (1 - config.hybrid_alpha) * (result.keyword_score or 0)
                    result.method = RetrievalMethod.HYBRID
                    doc_map[doc_id] = result
        
        # 转换为列表并排序
        merged_results = list(doc_map.values())
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results[:config.top_k]
    
    async def retrieve(
        self,
        query: str,
        config: RetrievalConfig
    ) -> List[RetrievalResult]:
        """执行混合检索"""
        try:
            logger.debug(f"执行混合检索: {query[:50]}...")
            
            # 并行执行向量检索和关键词检索
            if config.enable_parallel:
                vector_task = self.vector_retriever.retrieve(query, config)
                keyword_task = self.keyword_retriever.retrieve(query, config)
                
                vector_results, keyword_results = await asyncio.gather(
                    vector_task, keyword_task, return_exceptions=True
                )
                
                # 处理异常
                if isinstance(vector_results, Exception):
                    logger.error(f"向量检索异常: {vector_results}")
                    vector_results = []
                if isinstance(keyword_results, Exception):
                    logger.error(f"关键词检索异常: {keyword_results}")
                    keyword_results = []
            else:
                # 串行执行
                vector_results = await self.vector_retriever.retrieve(query, config)
                keyword_results = await self.keyword_retriever.retrieve(query, config)
            
            # 合并结果
            merged_results = self._merge_results(vector_results, keyword_results, config)
            
            logger.info(f"混合检索完成，返回 {len(merged_results)} 个结果")
            return merged_results

        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            return []


class RerankerService:
    """重排序服务"""

    def __init__(self):
        self.quality_keywords = {
            "高质量": ["详细", "完整", "准确", "专业", "权威", "官方"],
            "中等质量": ["基本", "一般", "简单", "概述"],
            "低质量": ["不完整", "错误", "过时", "简陋"]
        }

    def _calculate_relevance_score(self, query: str, result: RetrievalResult) -> float:
        """计算相关性分数"""
        # 基于现有分数
        base_score = result.score

        # 考虑查询词在文档中的位置（标题、开头更重要）
        content = result.document.page_content.lower()
        query_lower = query.lower()

        position_bonus = 0.0
        if query_lower in content[:100]:  # 在前100字符中
            position_bonus = 0.2
        elif query_lower in content[:500]:  # 在前500字符中
            position_bonus = 0.1

        return min(1.0, base_score + position_bonus)

    def _calculate_time_score(self, result: RetrievalResult) -> float:
        """计算时间分数（越新越好）"""
        # 从元数据中获取时间信息
        timestamp = result.document.metadata.get("timestamp")
        if not timestamp:
            return 0.5  # 默认中等分数

        try:
            # 简化处理，实际应该解析具体的时间格式
            current_time = time.time()
            doc_time = float(timestamp)

            # 计算时间差（天）
            time_diff_days = (current_time - doc_time) / (24 * 3600)

            # 时间衰减函数
            if time_diff_days <= 1:
                return 1.0
            elif time_diff_days <= 7:
                return 0.8
            elif time_diff_days <= 30:
                return 0.6
            elif time_diff_days <= 90:
                return 0.4
            else:
                return 0.2

        except (ValueError, TypeError):
            return 0.5

    def _calculate_quality_score(self, result: RetrievalResult) -> float:
        """计算质量分数"""
        content = result.document.page_content.lower()

        # 基于内容长度的质量评估
        length_score = min(1.0, len(content) / 1000)  # 1000字符为满分

        # 基于关键词的质量评估
        quality_score = 0.5  # 默认分数

        for quality_level, keywords in self.quality_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    if quality_level == "高质量":
                        quality_score = max(quality_score, 0.9)
                    elif quality_level == "中等质量":
                        quality_score = max(quality_score, 0.6)
                    elif quality_level == "低质量":
                        quality_score = min(quality_score, 0.3)

        # 综合长度和关键词分数
        return (length_score + quality_score) / 2

    def _calculate_hybrid_score(
        self,
        query: str,
        result: RetrievalResult,
        weights: Dict[str, float] = None
    ) -> float:
        """计算混合分数"""
        if weights is None:
            weights = {
                "relevance": 0.5,
                "time": 0.2,
                "quality": 0.3
            }

        relevance_score = self._calculate_relevance_score(query, result)
        time_score = self._calculate_time_score(result)
        quality_score = self._calculate_quality_score(result)

        hybrid_score = (
            weights["relevance"] * relevance_score +
            weights["time"] * time_score +
            weights["quality"] * quality_score
        )

        return hybrid_score

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        method: RerankingMethod,
        top_k: int = None
    ) -> List[RetrievalResult]:
        """重排序检索结果"""
        if not results:
            return results

        try:
            logger.debug(f"开始重排序，方法: {method}, 结果数量: {len(results)}")

            # 计算重排序分数
            for result in results:
                if method == RerankingMethod.RELEVANCE:
                    result.rerank_score = self._calculate_relevance_score(query, result)
                elif method == RerankingMethod.TIME:
                    result.rerank_score = self._calculate_time_score(result)
                elif method == RerankingMethod.QUALITY:
                    result.rerank_score = self._calculate_quality_score(result)
                elif method == RerankingMethod.HYBRID_SCORE:
                    result.rerank_score = self._calculate_hybrid_score(query, result)
                else:
                    result.rerank_score = result.score

            # 按重排序分数排序
            reranked_results = sorted(results, key=lambda x: x.rerank_score or 0, reverse=True)

            # 返回top_k结果
            if top_k:
                reranked_results = reranked_results[:top_k]

            logger.info(f"重排序完成，返回 {len(reranked_results)} 个结果")
            return reranked_results

        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return results  # 返回原始结果


class EnhancedRetriever:
    """增强检索器主类"""

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: MilvusVectorStore
    ):
        self.embedding_model = embedding_model
        self.vector_store = vector_store

        # 初始化各种检索器
        self.vector_retriever = VectorRetriever(embedding_model, vector_store)
        self.keyword_retriever = KeywordRetriever(vector_store)
        self.hybrid_retriever = HybridRetriever(self.vector_retriever, self.keyword_retriever)

        # 初始化重排序服务
        self.reranker = RerankerService()

    async def retrieve(
        self,
        query: str,
        config: RetrievalConfig = None
    ) -> List[RetrievalResult]:
        """执行增强检索"""
        if config is None:
            config = RetrievalConfig()

        try:
            logger.info(f"开始增强检索，方法: {config.method}, 查询: {query[:50]}...")
            start_time = time.time()

            # 根据配置选择检索方法
            if config.method == RetrievalMethod.VECTOR:
                results = await self.vector_retriever.retrieve(query, config)
            elif config.method == RetrievalMethod.KEYWORD:
                results = await self.keyword_retriever.retrieve(query, config)
            elif config.method == RetrievalMethod.HYBRID:
                results = await self.hybrid_retriever.retrieve(query, config)
            else:
                # 默认使用向量检索
                results = await self.vector_retriever.retrieve(query, config)

            # 执行重排序
            if config.enable_reranking and results:
                # 获取更多候选结果用于重排序
                rerank_config = RetrievalConfig(
                    method=config.method,
                    top_k=config.reranking_top_k,
                    score_threshold=config.score_threshold * 0.5  # 降低阈值获取更多候选
                )

                if len(results) < config.reranking_top_k:
                    # 如果结果不够，重新检索更多候选
                    if config.method == RetrievalMethod.VECTOR:
                        candidate_results = await self.vector_retriever.retrieve(query, rerank_config)
                    elif config.method == RetrievalMethod.KEYWORD:
                        candidate_results = await self.keyword_retriever.retrieve(query, rerank_config)
                    elif config.method == RetrievalMethod.HYBRID:
                        candidate_results = await self.hybrid_retriever.retrieve(query, rerank_config)
                    else:
                        candidate_results = results
                else:
                    candidate_results = results

                # 执行重排序
                results = await self.reranker.rerank(
                    query=query,
                    results=candidate_results,
                    method=config.reranking_method,
                    top_k=config.top_k
                )

            elapsed_time = time.time() - start_time
            logger.info(f"增强检索完成，耗时: {elapsed_time:.3f}s, 返回 {len(results)} 个结果")

            return results

        except Exception as e:
            logger.error(f"增强检索失败: {str(e)}")
            return []

    async def batch_retrieve(
        self,
        queries: List[str],
        config: RetrievalConfig = None
    ) -> List[List[RetrievalResult]]:
        """批量检索"""
        if config is None:
            config = RetrievalConfig()

        try:
            logger.info(f"开始批量检索，查询数量: {len(queries)}")

            if config.enable_parallel:
                # 并行处理
                tasks = [self.retrieve(query, config) for query in queries]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理异常
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"查询 {i} 失败: {result}")
                        processed_results.append([])
                    else:
                        processed_results.append(result)

                return processed_results
            else:
                # 串行处理
                results = []
                for query in queries:
                    result = await self.retrieve(query, config)
                    results.append(result)

                return results

        except Exception as e:
            logger.error(f"批量检索失败: {str(e)}")
            return [[] for _ in queries]
