import json
import redis
import logging
import os
from typing import Optional, List, Dict, Any
from .document_processor import Document

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化缓存服务
        
        Args:
            config: 缓存配置，如果未提供则从环境变量读取
        """
        # 从环境变量读取配置，如果未提供
        if config is None:
            config = {
                "host": os.environ.get("REDIS_HOST", "localhost"),
                "port": int(os.environ.get("REDIS_PORT", "6379")),
                "db": int(os.environ.get("REDIS_DB", "0")),
                "key_prefix": os.environ.get("REDIS_KEY_PREFIX", "rag_cache:"),
                "expiry": int(os.environ.get("REDIS_CACHE_EXPIRY", "3600"))
            }
        
        try:
            self.redis_client = redis.Redis(
                host=config.get("host", "localhost"),
                port=config.get("port", 6379),
                db=config.get("db", 0),
                decode_responses=True
            )
            self.key_prefix = config.get("key_prefix", "rag_cache:")
            self.expiry = config.get("expiry", 3600)  # 默认1小时过期
            
            # 测试连接
            self.redis_client.ping()
            logger.info(f"已成功连接到Redis: {config.get('host')}:{config.get('port')}")
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis连接失败，缓存服务将被禁用: {str(e)}")
            self.enabled = False
        
    def get_cached_results(self, query: str, dataset_id: str) -> Optional[List[Document]]:
        """获取缓存的检索结果"""
        if not self.enabled:
            return None
            
        try:
            cache_key = f"{self.key_prefix}retrieval:{dataset_id}:{query}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # 反序列化缓存的数据
                data = json.loads(cached_data)
                return [Document(page_content=doc["page_content"], metadata=doc["metadata"]) for doc in data]
            return None
        except Exception as e:
            logger.warning(f"获取缓存结果失败: {str(e)}")
            return None
        
    def cache_results(self, query: str, dataset_id: str, results: List[Document]) -> None:
        """缓存检索结果"""
        if not self.enabled or not results:
            return
            
        try:
            cache_key = f"{self.key_prefix}retrieval:{dataset_id}:{query}"
            
            # 序列化文档数据
            data = [
                {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in results
            ]
            
            # 存储到Redis
            self.redis_client.setex(
                cache_key,
                self.expiry,
                json.dumps(data)
            )
            logger.debug(f"查询结果已缓存: {query}")
        except Exception as e:
            logger.warning(f"缓存结果失败: {str(e)}")
            
    def invalidate_cache(self, dataset_id: str) -> None:
        """使指定数据集的所有缓存失效"""
        if not self.enabled:
            return
            
        try:
            pattern = f"{self.key_prefix}retrieval:{dataset_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"已清除数据集 {dataset_id} 的 {len(keys)} 条缓存")
        except Exception as e:
            logger.warning(f"使缓存失效失败: {str(e)}")
            
    def clear_all_cache(self) -> None:
        """清除所有缓存"""
        if not self.enabled:
            return
            
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"已清除所有 {len(keys)} 条缓存")
        except Exception as e:
            logger.warning(f"清除所有缓存失败: {str(e)}") 