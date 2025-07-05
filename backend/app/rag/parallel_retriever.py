"""
并行检索优化模块
实现高性能的并行检索处理
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import concurrent.futures
from functools import partial

from .enhanced_retriever import (
    EnhancedRetriever, 
    RetrievalConfig, 
    RetrievalResult, 
    RetrievalMethod
)
from .advanced_reranker import AdvancedRerankerService, RerankingConfig

logger = logging.getLogger(__name__)


class ParallelStrategy(str, Enum):
    """并行策略枚举"""
    ASYNC_CONCURRENT = "async_concurrent"      # 异步并发
    THREAD_POOL = "thread_pool"               # 线程池
    PROCESS_POOL = "process_pool"             # 进程池
    HYBRID = "hybrid"                         # 混合策略


@dataclass
class ParallelConfig:
    """并行配置"""
    strategy: ParallelStrategy = ParallelStrategy.ASYNC_CONCURRENT
    max_workers: int = 4                      # 最大工作线程/进程数
    timeout_seconds: float = 30.0             # 超时时间
    batch_size: int = 10                      # 批处理大小
    enable_caching: bool = True               # 启用缓存
    cache_ttl_seconds: int = 300              # 缓存TTL
    enable_circuit_breaker: bool = True       # 启用熔断器
    failure_threshold: int = 5                # 失败阈值
    recovery_timeout: int = 60                # 恢复超时


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """执行函数调用，带熔断保护"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("熔断器进入半开状态")
            else:
                raise Exception("熔断器开启，拒绝请求")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("熔断器恢复到关闭状态")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
            
            raise e


class QueryCache:
    """查询缓存"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[List[RetrievalResult]]:
        """获取缓存结果"""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                logger.debug(f"缓存命中: {key}")
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: List[RetrievalResult]):
        """设置缓存结果"""
        self.cache[key] = (value, time.time())
        logger.debug(f"缓存设置: {key}")
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")


class ParallelRetriever:
    """并行检索器"""
    
    def __init__(
        self,
        enhanced_retriever: EnhancedRetriever,
        reranker_service: Optional[AdvancedRerankerService] = None
    ):
        self.enhanced_retriever = enhanced_retriever
        self.reranker_service = reranker_service or AdvancedRerankerService()
        self.cache = QueryCache()
        self.circuit_breaker = CircuitBreaker()
        
        # 性能统计
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "parallel_executions": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
    
    async def parallel_retrieve(
        self,
        queries: List[str],
        config: ParallelConfig = None,
        retrieval_config: RetrievalConfig = None
    ) -> List[List[RetrievalResult]]:
        """并行检索多个查询"""
        if config is None:
            config = ParallelConfig()
        if retrieval_config is None:
            retrieval_config = RetrievalConfig()

        start_time = time.time()
        self.stats["total_queries"] += len(queries)

        try:
            logger.info(f"开始并行检索，查询数量: {len(queries)}, 策略: {config.strategy}")

            # 检查缓存
            cached_results = []
            uncached_queries = []
            query_indices = []

            if config.enable_caching:
                for i, query in enumerate(queries):
                    cache_key = self._generate_cache_key(query, retrieval_config)
                    cached_result = self.cache.get(cache_key)
                    if cached_result is not None:
                        cached_results.append((i, cached_result))
                        self.stats["cache_hits"] += 1
                    else:
                        uncached_queries.append(query)
                        query_indices.append(i)
            else:
                uncached_queries = queries
                query_indices = list(range(len(queries)))

            # 并行处理未缓存的查询
            uncached_results = []
            if uncached_queries:
                self.stats["parallel_executions"] += 1

                if config.strategy == ParallelStrategy.ASYNC_CONCURRENT:
                    uncached_results = await self._async_concurrent_retrieve(
                        uncached_queries, config, retrieval_config
                    )
                elif config.strategy == ParallelStrategy.THREAD_POOL:
                    uncached_results = await self._thread_pool_retrieve(
                        uncached_queries, config, retrieval_config
                    )
                elif config.strategy == ParallelStrategy.PROCESS_POOL:
                    uncached_results = await self._process_pool_retrieve(
                        uncached_queries, config, retrieval_config
                    )
                elif config.strategy == ParallelStrategy.HYBRID:
                    uncached_results = await self._hybrid_retrieve(
                        uncached_queries, config, retrieval_config
                    )

                # 缓存结果
                if config.enable_caching:
                    for query, result in zip(uncached_queries, uncached_results):
                        cache_key = self._generate_cache_key(query, retrieval_config)
                        self.cache.set(cache_key, result)

            # 合并结果
            final_results = [None] * len(queries)

            # 填入缓存结果
            for i, result in cached_results:
                final_results[i] = result

            # 填入新检索结果
            for i, result in zip(query_indices, uncached_results):
                final_results[i] = result

            # 更新统计信息
            elapsed_time = time.time() - start_time
            if self.stats["total_queries"] > 0:
                self.stats["average_response_time"] = (
                    (self.stats["average_response_time"] * (self.stats["total_queries"] - len(queries)) +
                     elapsed_time) / self.stats["total_queries"]
                )

            logger.info(f"并行检索完成，耗时: {elapsed_time:.3f}s, 缓存命中: {len(cached_results)}/{len(queries)}")
            return final_results

        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"并行检索失败: {str(e)}")
            raise e
    
    async def _async_concurrent_retrieve(
        self,
        queries: List[str],
        config: ParallelConfig,
        retrieval_config: RetrievalConfig
    ) -> List[List[RetrievalResult]]:
        """异步并发检索"""
        semaphore = asyncio.Semaphore(config.max_workers)
        
        async def retrieve_with_semaphore(query: str):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self.enhanced_retriever.retrieve(query, retrieval_config),
                        timeout=config.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"查询超时: {query[:50]}...")
                    return []
                except Exception as e:
                    logger.error(f"查询失败: {query[:50]}..., 错误: {str(e)}")
                    return []
        
        tasks = [retrieve_with_semaphore(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"检索任务异常: {str(result)}")
                processed_results.append([])
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _thread_pool_retrieve(
        self,
        queries: List[str],
        config: ParallelConfig,
        retrieval_config: RetrievalConfig
    ) -> List[List[RetrievalResult]]:
        """线程池检索"""
        loop = asyncio.get_event_loop()
        
        def sync_retrieve(query: str):
            try:
                # 在线程中运行异步函数
                return asyncio.run(self.enhanced_retriever.retrieve(query, retrieval_config))
            except Exception as e:
                logger.error(f"线程池检索失败: {query[:50]}..., 错误: {str(e)}")
                return []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = [
                loop.run_in_executor(executor, sync_retrieve, query)
                for query in queries
            ]
            results = await asyncio.gather(*futures, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"线程池任务异常: {str(result)}")
                processed_results.append([])
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_pool_retrieve(
        self,
        queries: List[str],
        config: ParallelConfig,
        retrieval_config: RetrievalConfig
    ) -> List[List[RetrievalResult]]:
        """进程池检索（简化实现）"""
        # 注意：进程池需要序列化，这里简化为线程池实现
        logger.warning("进程池检索暂时使用线程池实现")
        return await self._thread_pool_retrieve(queries, config, retrieval_config)
    
    async def _hybrid_retrieve(
        self,
        queries: List[str],
        config: ParallelConfig,
        retrieval_config: RetrievalConfig
    ) -> List[List[RetrievalResult]]:
        """混合策略检索"""
        # 根据查询数量选择策略
        if len(queries) <= 5:
            return await self._async_concurrent_retrieve(queries, config, retrieval_config)
        else:
            return await self._thread_pool_retrieve(queries, config, retrieval_config)
    
    def _generate_cache_key(self, query: str, config: RetrievalConfig) -> str:
        """生成缓存键"""
        return f"{query}:{config.method}:{config.top_k}:{hash(str(config))}"
    
    async def batch_retrieve_with_reranking(
        self,
        queries: List[str],
        parallel_config: ParallelConfig = None,
        retrieval_config: RetrievalConfig = None,
        reranking_config: RerankingConfig = None
    ) -> List[List[RetrievalResult]]:
        """批量检索并重排序"""
        # 先进行并行检索
        retrieval_results = await self.parallel_retrieve(
            queries, parallel_config, retrieval_config
        )
        
        # 对每个查询的结果进行重排序
        if reranking_config and self.reranker_service:
            reranked_results = []
            for query, results in zip(queries, retrieval_results):
                if results:
                    reranked = await self.reranker_service.rerank(
                        query, results, reranking_config
                    )
                    reranked_results.append(reranked)
                else:
                    reranked_results.append([])
            return reranked_results
        
        return retrieval_results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "parallel_executions": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
        logger.info("统计信息已重置")
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")
