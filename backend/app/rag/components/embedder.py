"""
向量嵌入器组件

实现文本向量化功能，支持多种嵌入模型。
实现IEmbedder接口，提供统一的向量嵌入功能。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import openai
from openai import AsyncOpenAI

from app.rag.interfaces import BaseEmbedder
from app.core.config import settings

logger = logging.getLogger(__name__)

class Embedder(BaseEmbedder):
    """向量嵌入器实现"""
    
    def __init__(
        self,
        model_name: str = "text-embedding-ada-002",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3
    ):
        """
        初始化向量嵌入器
        
        Args:
            model_name: 嵌入模型名称
            api_key: API密钥
            api_base: API基础URL
            batch_size: 批处理大小
            max_retries: 最大重试次数
        """
        self.model_name = model_name
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = api_base or settings.EMBEDDING_API_BASE
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
        # 模型维度映射
        self._dimension_map = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-nomic-embed-text-v1.5": 768
        }
    
    async def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        Args:
            text: 要向量化的文本
            
        Returns:
            List[float]: 向量表示
        """
        if not text.strip():
            return [0.0] * self.dimension
        
        try:
            response = await self._call_embedding_api([text])
            return response[0]
        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            raise
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文本进行批量向量化
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            List[List[float]]: 向量表示列表
        """
        if not texts:
            return []
        
        # 过滤空文本
        valid_texts = [text for text in texts if text.strip()]
        if not valid_texts:
            return [[0.0] * self.dimension] * len(texts)
        
        # 批量处理
        all_embeddings = []
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i:i + self.batch_size]
            try:
                batch_embeddings = await self._call_embedding_api(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"批量向量化失败 (batch {i//self.batch_size + 1}): {e}")
                # 为失败的批次返回零向量
                all_embeddings.extend([[0.0] * self.dimension] * len(batch))
        
        return all_embeddings
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        return self._dimension_map.get(self.model_name, 1536)
    
    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """
        调用嵌入API
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 向量列表
        """
        for attempt in range(self.max_retries):
            try:
                # 预处理文本
                processed_texts = [self._preprocess_text(text) for text in texts]
                
                # 调用API
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=processed_texts
                )
                
                # 提取向量
                embeddings = [data.embedding for data in response.data]
                
                logger.debug(f"成功获取 {len(embeddings)} 个向量")
                return embeddings
                
            except openai.RateLimitError as e:
                wait_time = 2 ** attempt
                logger.warning(f"API限流，等待 {wait_time} 秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)
                
            except openai.APIError as e:
                logger.error(f"API错误: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"向量化API调用失败: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception(f"向量化失败，已重试 {self.max_retries} 次")
    
    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 预处理后的文本
        """
        # 移除多余的空白字符
        text = " ".join(text.split())
        
        # 限制文本长度（OpenAI有token限制）
        max_length = 8000  # 保守估计
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"文本被截断到 {max_length} 字符")
        
        return text
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "max_retries": self.max_retries,
            "api_base": self.api_base
        }
    
    def set_batch_size(self, batch_size: int) -> None:
        """设置批处理大小"""
        self.batch_size = max(1, batch_size)
    
    def set_max_retries(self, max_retries: int) -> None:
        """设置最大重试次数"""
        self.max_retries = max(0, max_retries)
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 服务是否可用
        """
        try:
            test_embedding = await self.embed_text("测试文本")
            return len(test_embedding) == self.dimension
        except Exception as e:
            logger.error(f"嵌入服务健康检查失败: {e}")
            return False
