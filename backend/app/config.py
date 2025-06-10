"""配置文件"""

import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # RAG ETL配置
    ETL_TYPE: str = "dify"  # 'dify' 或 'Unstructured'
    
    # Unstructured API配置
    UNSTRUCTURED_API_URL: Optional[str] = None
    UNSTRUCTURED_API_KEY: str = ""
    
    # 其他配置...
    
    class Config:
        env_file = ".env"
        
settings = Settings() 