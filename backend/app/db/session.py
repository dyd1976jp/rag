"""
数据库会话管理

统一管理各种数据库的会话和连接，提供依赖注入接口。
支持MongoDB、Milvus等多种数据库的会话管理。
"""

import logging
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.database import Database
from pymilvus import Collection

from .connections.mongodb import mongodb_manager
from .connections.milvus import milvus_manager

logger = logging.getLogger(__name__)


# MongoDB会话管理
async def get_async_mongodb() -> AsyncIOMotorDatabase:
    """
    获取异步MongoDB数据库实例

    用于FastAPI依赖注入
    """
    return await mongodb_manager.get_async_database()


def get_sync_mongodb() -> Database:
    """
    获取同步MongoDB数据库实例

    用于同步操作
    """
    return mongodb_manager.get_sync_database()


@asynccontextmanager
async def async_mongodb_session() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    异步MongoDB会话上下文管理器

    使用示例:
        async with async_mongodb_session() as db:
            collection = db.documents
            await collection.insert_one(document)
    """
    try:
        db = await mongodb_manager.get_async_database()
        yield db
    except Exception as e:
        logger.error(f"MongoDB会话错误: {str(e)}")
        raise
    finally:
        # MongoDB连接池会自动管理连接，无需手动关闭
        pass


@contextmanager
def sync_mongodb_session() -> Generator[Database, None, None]:
    """
    同步MongoDB会话上下文管理器

    使用示例:
        with sync_mongodb_session() as db:
            collection = db.documents
            collection.insert_one(document)
    """
    try:
        db = mongodb_manager.get_sync_database()
        yield db
    except Exception as e:
        logger.error(f"MongoDB会话错误: {str(e)}")
        raise
    finally:
        # MongoDB连接池会自动管理连接，无需手动关闭
        pass


# Milvus会话管理
def get_milvus_collection(collection_name: str = None) -> Collection:
    """
    获取Milvus集合实例

    用于FastAPI依赖注入
    """
    return milvus_manager.get_collection(collection_name)


@contextmanager
def milvus_session(collection_name: str = None) -> Generator[Collection, None, None]:
    """
    Milvus会话上下文管理器

    使用示例:
        with milvus_session() as collection:
            collection.insert(data)
    """
    try:
        collection = milvus_manager.get_collection(collection_name)
        if collection is None:
            raise RuntimeError(f"无法获取Milvus集合: {collection_name}")
        yield collection
    except Exception as e:
        logger.error(f"Milvus会话错误: {str(e)}")
        raise
    finally:
        # Milvus连接由管理器维护，无需手动关闭
        pass


# 数据库会话依赖注入函数
async def get_db_session():
    """
    通用数据库会话依赖注入

    返回包含各种数据库连接的会话对象
    """
    return {
        "mongodb": await get_async_mongodb(),
        "milvus": get_milvus_collection()
    }


# 兼容性函数，保持向后兼容
def get_db():
    """兼容性函数，保持向后兼容"""
    return get_sync_mongodb()