"""
应用程序配置模块

本模块负责加载和管理应用程序的配置参数，包括：
1. 环境变量处理和多环境支持
2. 应用程序基本信息
3. 数据库连接配置
4. 安全设置
5. API外部服务连接参数
6. 文件存储和上传限制
7. CORS策略
8. 日志和监控配置

配置参数优先从环境变量加载，支持多环境配置文件。
通过APP_ENV环境变量控制加载不同环境的配置文件。
"""

from typing import List, Optional, Literal
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator, ConfigDict, validator
from dotenv import load_dotenv
import os
from pathlib import Path
from .paths import (
    UPLOADS_DIR, CHROMA_DIR, APP_LOGS_DIR,
    get_env_path, PROJECT_ROOT
)

# 环境类型定义
EnvironmentType = Literal["development", "test", "production"]

def load_env_file():
    """
    根据APP_ENV环境变量加载对应的配置文件

    优先级：
    1. APP_ENV指定的环境文件 (.env.{APP_ENV})
    2. 默认.env文件
    3. 环境变量
    """
    app_env = os.getenv("APP_ENV", "development")

    # 尝试加载环境特定的配置文件
    env_file = PROJECT_ROOT / f".env.{app_env}"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已加载环境配置文件: {env_file}")
    else:
        # 回退到默认.env文件
        default_env = PROJECT_ROOT / ".env"
        if default_env.exists():
            load_dotenv(default_env)
            print(f"✅ 已加载默认配置文件: {default_env}")
        else:
            print("⚠️ 未找到配置文件，将使用环境变量和默认值")

# 加载环境配置
load_env_file()

class Settings(BaseSettings):
    """
    应用程序配置类

    使用Pydantic的BaseSettings管理所有配置参数，支持从环境变量、
    多环境.env文件以及默认值加载配置。所有配置参数都有类型注解以确保类型安全。

    环境配置文件加载顺序：
    1. .env.{APP_ENV} (如 .env.development, .env.test, .env.production)
    2. .env (默认配置文件)
    3. 环境变量
    4. 默认值
    """
    # ==================== 基础配置 ====================
    PROJECT_NAME: str = "RAG Chat"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "基于 RAG 技术的智能聊天应用"

    # ==================== 环境配置 ====================
    APP_ENV: EnvironmentType = "development"
    ENVIRONMENT: EnvironmentType = "development"  # 兼容旧配置
    DEBUG: bool = False

    # ==================== 日志配置 ====================
    LOGLEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FILE: str = str(APP_LOGS_DIR / "app.log")
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    # ==================== 安全配置 ====================
    SECRET_KEY: str = "your-secret-key-here-please-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # ==================== 数据库配置 ====================
    # MongoDB配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "ragchat"
    MONGODB_DB_NAME: str = "ragchat"  # 兼容性别名

    # Milvus向量数据库配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_USER: Optional[str] = None
    MILVUS_PASSWORD: Optional[str] = None
    MILVUS_COLLECTION: str = "documents"
    MILVUS_DIM: int = 1536  # OpenAI text-embedding-ada-002 的维度

    # ==================== AI/LLM配置 ====================
    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-ada-002"

    # 本地模型配置
    LOCAL_MODEL_URL: str = "http://localhost:1234"
    EMBEDDING_API_BASE: str = "http://localhost:1234/v1"

    # ==================== 文件存储配置 ====================
    UPLOAD_DIR: str = str(get_env_path("UPLOAD_DIR", UPLOADS_DIR))
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    CHROMA_PERSIST_DIRECTORY: str = str(get_env_path("CHROMA_PERSIST_DIR", CHROMA_DIR))

    # ==================== 文档处理配置 ====================
    MAX_FILE_SIZE: int = 104857600  # 默认100MB
    PROCESSING_TIMEOUT: int = 1800  # 默认30分钟
    MAX_SEGMENTS: int = 100000  # 默认最多10万段落
    SPLITTER_TIMEOUT: int = 300  # 默认分割超时5分钟

    # ==================== ETL配置 ====================
    ETL_TYPE: str = "Unstructured"
    UNSTRUCTURED_API_URL: str = "your_api_url"
    UNSTRUCTURED_API_KEY: str = "your_api_key"

    # ==================== CORS配置 ====================
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # 兼容旧配置
        "http://localhost:5173",  # frontend-app (Vite默认端口)
        "http://localhost:5174",  # frontend-admin (Vite默认端口)
        "http://localhost:3001",  # 备用前端端口
    ]

    # ==================== 性能配置 ====================
    # 并发和性能相关配置
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 50
    CACHE_TTL: int = 3600  # 缓存过期时间（秒）

    # ==================== 监控配置 ====================
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 30  # 健康检查间隔（秒）

    # ==================== RAG系统配置 ====================
    # 检索配置
    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.0
    RAG_SCORE_THRESHOLD_ENABLED: bool = False
    RAG_MAX_RETRIES: int = 3
    RAG_RETRY_INTERVAL: int = 5

    # 文档处理配置
    RAG_REMOVE_HTML: bool = True
    RAG_REMOVE_EXTRA_SPACES: bool = True
    RAG_REMOVE_URLS: bool = True
    RAG_SEPARATOR: str = "\n\n"
    RAG_MAX_TOKENS: int = 512
    RAG_CHUNK_OVERLAP: int = 100

    # 嵌入模型配置
    RAG_EMBEDDING_MODEL: str = "text-embedding-nomic-embed-text-v1.5"
    RAG_EMBEDDING_API_BASE: str = "http://localhost:1234"
    RAG_EMBEDDING_DIMENSION: int = 768

    # ==================== Redis缓存配置 ====================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_KEY_PREFIX: str = "rag_cache:"

    # ==================== 管理员配置 ====================
    ADMIN_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_SECRET_KEY: Optional[str] = None  # 如果未设置，使用主SECRET_KEY

    # ==================== 验证器 ====================
    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v):
        """
        CORS源验证器

        处理CORS来源配置，支持从字符串(逗号分隔)或列表加载。
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(f"Invalid CORS origins format: {v}")

    @validator("APP_ENV", "ENVIRONMENT")
    def validate_environment(cls, v):
        """验证环境配置"""
        if v not in ["development", "test", "production"]:
            raise ValueError(f"Invalid environment: {v}. Must be one of: development, test, production")
        return v

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        """验证密钥安全性"""
        if values.get("APP_ENV") == "production" and v == "your-secret-key-here-please-change-in-production":
            raise ValueError("SECRET_KEY must be changed in production environment")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @validator("MONGODB_URL")
    def validate_mongodb_url(cls, v):
        """验证MongoDB连接字符串"""
        if not v.startswith("mongodb://") and not v.startswith("mongodb+srv://"):
            raise ValueError("MONGODB_URL must start with 'mongodb://' or 'mongodb+srv://'")
        return v

    # ==================== Pydantic配置 ====================
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",  # 允许额外的字段
        validate_assignment=True,  # 赋值时验证
        use_enum_values=True,  # 使用枚举值
    )

def get_settings() -> Settings:
    """
    获取配置实例

    使用函数而不是直接实例化，便于测试时mock配置。
    """
    return Settings()

# 实例化配置对象，供应用程序其他部分使用
settings = get_settings()

# 导出常用配置，便于其他模块使用
__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "EnvironmentType",
    "load_env_file"
]