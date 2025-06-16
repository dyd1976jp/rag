"""
嵌入模型模块
"""

import os
import time
import logging
import requests
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingModel:
    """嵌入模型类"""
    
    def __init__(self):
        # 从环境变量获取配置
        self.model_name = os.environ.get("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
        self.api_base = os.environ.get("EMBEDDING_API_BASE", "http://192.168.1.30:1234")
        
        # 批处理配置
        self.max_batch_size = int(os.environ.get("EMBEDDING_MAX_BATCH_SIZE", "20"))
        self.max_retries = int(os.environ.get("EMBEDDING_MAX_RETRIES", "3"))
        self.retry_delay = int(os.environ.get("EMBEDDING_RETRY_DELAY", "5"))
        self.timeout = int(os.environ.get("EMBEDDING_TIMEOUT", "30"))
        
        logger.info(f"初始化嵌入模型: 模型={self.model_name}, API地址={self.api_base}")
        logger.info(f"批处理配置: 最大批量={self.max_batch_size}, 重试次数={self.max_retries}, 重试间隔={self.retry_delay}秒, 超时={self.timeout}秒")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """生成文档的嵌入向量"""
        try:
            # 计算文本长度统计
            text_lengths = [len(text) for text in texts]
            avg_length = sum(text_lengths) / len(text_lengths)
            max_length = max(text_lengths)
            min_length = min(text_lengths)
            
            logger.info(f"开始处理 {len(texts)} 个文本的嵌入向量，总字符数: {sum(text_lengths)}")
            logger.info(f"文本长度统计 - 平均: {avg_length:.1f}, 最大: {max_length}, 最小: {min_length}")
            
            # 根据文本长度调整批量大小
            if avg_length > 1000:
                batch_size = min(self.max_batch_size // 2, 10)
                logger.info(f"检测到长文本(平均{avg_length:.0f}字符)，减小批量大小到{batch_size}")
            else:
                batch_size = self.max_batch_size
                logger.info(f"检测到标准长度文本(平均{avg_length:.0f}字符)，使用默认批量大小{batch_size}")
            
            # 如果文本数量小于批量大小，直接处理
            if len(texts) <= batch_size:
                logger.info(f"直接处理 {len(texts)} 个文本")
                return self._embed_batch_with_retry(texts)
            
            # 否则，分批处理
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(f"处理批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}, 大小: {len(batch)}")
                batch_embeddings = self._embed_batch_with_retry(batch)
                embeddings.extend(batch_embeddings)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"文档嵌入失败: {str(e)}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise
    
    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        """带重试机制的批量嵌入"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # 准备请求数据
                data = {
                    "model": self.model_name,
                    "prompt": texts[0] if len(texts) == 1 else texts,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": 2048
                    }
                }
                
                # 发送请求
                response = requests.post(
                    f"{self.api_base}/api/embeddings",
                    json=data,
                    timeout=self.timeout
                )
                
                # 检查响应
                if response.status_code == 200:
                    result = response.json()
                    if "data" in result and len(result["data"]) > 0:
                        embeddings = [item["embedding"] for item in result["data"]]
                        return embeddings
                
                # 如果响应不成功，抛出异常
                raise Exception(f"API调用失败: {response.text}")
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"批量嵌入失败 (尝试 {attempt+1}/{self.max_retries}): {str(e)}，{self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"批量嵌入在 {self.max_retries} 次尝试后失败: {str(e)}")
        
        raise last_error

    def embed_query(self, text: str) -> List[float]:
        """将单个文本转换为向量，适配 OpenAI 兼容 embedding API"""
        try:
            # 调用 OpenAI 兼容 API
            response = requests.post(
                f"{self.api_base}/v1/embeddings",
                json={
                    "model": self.model_name,
                    "input": text
                },
                timeout=self.timeout
            )
            if response.status_code != 200:
                raise Exception(f"API调用失败: {response.text}")
            result = response.json()
            # 解析 embedding
            data = result.get("data")
            if not data or not isinstance(data, list) or not data[0].get("embedding"):
                raise Exception("未获取到嵌入向量")
            embedding = data[0]["embedding"]
            return embedding
        except Exception as e:
            logger.error(f"查询嵌入失败: {str(e)}")
            raise
            
    def get_dimension(self) -> int:
        """获取向量维度"""
        try:
            # 使用一个简单的测试文本获取向量维度
            test_embedding = self.embed_query("test")
            return len(test_embedding)
        except Exception as e:
            logger.error(f"获取向量维度失败: {str(e)}")
            raise 