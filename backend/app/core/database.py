import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

# MongoDB配置
MONGODB_HOST = os.environ.get("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.environ.get("MONGODB_PORT", "27017"))
MONGODB_DB = os.environ.get("MONGODB_DB", "rag_db")

_mongodb_client: Optional[MongoClient] = None
_mongodb_db: Optional[Database] = None

def get_mongodb_client() -> Database:
    """获取MongoDB客户端"""
    global _mongodb_client, _mongodb_db
    
    if _mongodb_db is None:
        try:
            # 连接到MongoDB
            _mongodb_client = MongoClient(
                host=MONGODB_HOST,
                port=MONGODB_PORT
            )
            
            # 获取数据库
            _mongodb_db = _mongodb_client[MONGODB_DB]
            logger.info("MongoDB连接成功")
            
        except Exception as e:
            logger.error(f"MongoDB连接失败: {str(e)}")
            raise
            
    return _mongodb_db

def get_collection(collection_name: str) -> Collection:
    """获取指定的集合"""
    db = get_mongodb_client()
    return db[collection_name] 