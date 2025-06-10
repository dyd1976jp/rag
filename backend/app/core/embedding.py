import os
import logging
import requests
from typing import Optional, List
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

# LM Studio配置
OPENAI_API_BASE = "http://192.168.1.30:1234/v1"  # LM Studio默认地址
MODEL_NAME = "text-embedding-nomic-embed-text-v1.5"

_embedding_model: Optional[Embeddings] = None

class LMStudioEmbeddings(Embeddings):
    """LM Studio嵌入模型"""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """生成文档的嵌入向量"""
        try:
            # 直接调用LM Studio的API
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                f"{OPENAI_API_BASE}/embeddings",
                headers=headers,
                json={
                    "model": MODEL_NAME,
                    "input": texts
                }
            )
            response.raise_for_status()
            
            # 提取嵌入向量
            embeddings = []
            for data in response.json()["data"]:
                embeddings.append(data["embedding"])
            
            return embeddings
            
        except Exception as e:
            logger.error(f"生成文档嵌入向量失败: {str(e)}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """生成查询的嵌入向量"""
        try:
            # 直接调用LM Studio的API
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                f"{OPENAI_API_BASE}/embeddings",
                headers=headers,
                json={
                    "model": MODEL_NAME,
                    "input": text
                }
            )
            response.raise_for_status()
            
            # 提取嵌入向量
            embedding = response.json()["data"][0]["embedding"]
            return embedding
            
        except Exception as e:
            logger.error(f"生成查询嵌入向量失败: {str(e)}")
            raise

def get_embedding_model() -> Embeddings:
    """获取嵌入模型实例"""
    global _embedding_model
    
    if _embedding_model is None:
        try:
            _embedding_model = LMStudioEmbeddings()
            logger.info(f"嵌入模型连接成功，使用API: {OPENAI_API_BASE}")
        except Exception as e:
            logger.error(f"嵌入模型连接失败: {str(e)}")
            raise
    
    return _embedding_model 