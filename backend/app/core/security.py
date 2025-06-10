"""
安全工具模块

本模块提供用户认证和授权相关的安全功能，包括：
1. 密码哈希和验证
2. JWT令牌生成与解析
3. 用户身份验证

使用业界标准的安全库实现，如passlib用于密码哈希，python-jose用于JWT处理。
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings

# 配置密码加密上下文，使用bcrypt算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    比较明文密码与存储的哈希密码是否匹配。
    
    Args:
        plain_password (str): 用户提供的明文密码
        hashed_password (str): 数据库中存储的哈希密码
        
    Returns:
        bool: 密码匹配返回True，否则返回False
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    对明文密码进行哈希处理，用于安全存储。
    
    Args:
        password (str): 用户的明文密码
        
    Returns:
        str: 生成的密码哈希值，可安全存储到数据库
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    根据提供的数据生成JWT令牌，用于用户身份验证。
    
    Args:
        data (dict): 要编码到令牌中的数据，通常包含用户标识
        expires_delta (Optional[timedelta]): 令牌过期时间，默认使用配置中的值
        
    Returns:
        str: 生成的JWT令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt 