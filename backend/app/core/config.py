"""
应用程序配置模块

本模块负责加载和管理应用程序的配置参数，包括：
1. 环境变量处理
2. 应用程序基本信息
3. 数据库连接配置
4. 安全设置
5. API外部服务连接参数
6. 文件存储和上传限制
7. CORS策略

配置参数优先从环境变量加载，如未设置则使用默认值。
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator, ConfigDict
from dotenv import load_dotenv
import os
from .paths import (
    UPLOADS_DIR, CHROMA_DIR, APP_LOGS_DIR,
    get_env_path
)

# 加载.env文件中的环境变量
load_dotenv()

class Settings(BaseSettings):
    """
    应用程序配置类
    
    使用Pydantic的BaseSettings管理所有配置参数，支持从环境变量、
    .env文件以及默认值加载配置。所有配置参数都有类型注解以确保类型安全。
    """
    # 基础配置
    PROJECT_NAME: str = "RAG Chat"
    API_V1_STR: str = "/api/v1"
    
    # 环境配置 - development, production, test
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # 日志配置
    LOGLEVEL: str = os.getenv("LOGLEVEL", "INFO")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # 数据库配置
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "ragchat")
    
    # Milvus配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION: str = os.getenv("MILVUS_COLLECTION", "documents")
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # 文件存储配置
    UPLOAD_DIR: str = str(get_env_path("UPLOAD_DIR", UPLOADS_DIR))
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 文档处理配置
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 默认100MB
    PROCESSING_TIMEOUT: int = int(os.getenv("PROCESSING_TIMEOUT", "1800"))  # 默认30分钟
    MAX_SEGMENTS: int = int(os.getenv("MAX_SEGMENTS", "100000"))  # 默认最多10万段落
    SPLITTER_TIMEOUT: int = int(os.getenv("SPLITTER_TIMEOUT", "300"))  # 默认分割超时5分钟
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",  # 兼容旧配置
        "http://localhost:5173",  # frontend-app (Vite默认端口)
        "http://localhost:5174",  # frontend-admin (Vite默认端口)
    ]
    
    # 向量数据库配置
    CHROMA_PERSIST_DIRECTORY: str = str(get_env_path("CHROMA_PERSIST_DIR", CHROMA_DIR))
    
    # JWT配置
    ALGORITHM: str = "HS256"
    
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "基于 RAG 技术的智能聊天应用"
    
    MILVUS_DIM: int = int(os.getenv("MILVUS_DIM", "1536"))  # OpenAI text-embedding-ada-002 的维度
    
    # 日志文件路径
    LOG_FILE: str = str(APP_LOGS_DIR / "app.log")

    # Unstructured API配置
    ETL_TYPE: str = os.getenv("ETL_TYPE", "Unstructured")
    UNSTRUCTURED_API_URL: str = os.getenv("UNSTRUCTURED_API_URL", "your_api_url")
    UNSTRUCTURED_API_KEY: str = os.getenv("UNSTRUCTURED_API_KEY", "your_api_key")
    
    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        """
        CORS源验证器
        
        处理CORS来源配置，支持从字符串(逗号分隔)或列表加载。
        
        Args:
            v (str | List[str]): 输入的CORS来源配置
            
        Returns:
            List[str] | str: 处理后的CORS来源列表或原始字符串
            
        Raises:
            ValueError: 当输入格式无效时抛出
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = ConfigDict(
        case_sensitive = True,
        env_file = ".env",
        extra = "allow"  # 允许额外的字段
    )

# 实例化配置对象，供应用程序其他部分使用
settings = Settings() 