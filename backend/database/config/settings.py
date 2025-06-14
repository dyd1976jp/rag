from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class DatabaseSettings(BaseSettings):
    # MongoDB配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "rag_chat"
    
    # Milvus配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_USER: Optional[str] = None
    MILVUS_PASSWORD: Optional[str] = None
    MILVUS_COLLECTION: str = "document_vectors"
    
    # 环境配置
    environment: str = "development"
    etl_type: str = "Unstructured"
    unstructured_api_url: Optional[str] = None
    unstructured_api_key: Optional[str] = None
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow"
    )

settings = DatabaseSettings() 