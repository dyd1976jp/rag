"""
用户数据模型模块

本模块定义了与用户相关的数据模型，用于：
1. API请求和响应的数据验证
2. 用户创建和更新的数据格式定义
3. 用户信息的数据库存储格式
4. 用户信息的对外展示格式

使用Pydantic模型实现，提供类型安全和自动验证功能。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    """
    用户基础模型
    
    包含用户的基本信息，作为其他用户相关模型的基类。
    定义了所有用户模型共有的字段和默认值。
    """
    email: EmailStr
    username: str
    is_active: bool = True
    is_superuser: bool = False
    is_admin: bool = False  # 管理员标志，用于控制文档管理等高级权限

class UserCreate(UserBase):
    """
    用户创建模型
    
    用于用户注册请求，包含创建用户所需的所有信息。
    在基础用户信息基础上添加了密码字段。
    """
    password: str

class UserInDB(UserBase):
    """
    数据库用户模型
    
    定义用户在数据库中的存储格式，包含系统生成的字段。
    存储密码的哈希值而不是明文密码，提高安全性。
    """
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime

class User(UserBase):
    """
    用户响应模型
    
    定义返回给客户端的用户信息格式。
    不包含敏感信息如密码或密码哈希值。
    """
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    } 