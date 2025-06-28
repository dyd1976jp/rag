"""
数据访问仓储模块

实现仓储模式，提供对各种数据存储的统一访问接口。
分离数据访问逻辑和业务逻辑，提高代码的可测试性和可维护性。
"""

from .base import BaseRepository
from .document import DocumentRepository
from .user import UserRepository
from .vector import VectorRepository

__all__ = [
    "BaseRepository",
    "DocumentRepository", 
    "UserRepository",
    "VectorRepository"
]
