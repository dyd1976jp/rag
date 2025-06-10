"""
用户服务模块

本模块提供与用户相关的业务逻辑服务，包括：
1. 用户创建与注册
2. 用户认证和登录
3. 用户信息查询
4. 密码处理和验证

作为应用程序与数据库之间的中间层，处理所有用户相关操作的逻辑。
"""

from datetime import datetime
from typing import Optional
import logging
from ..db.mongodb import mongodb
from ..models.user import UserCreate, UserInDB, User
from ..core.config import settings
from ..core.security import get_password_hash, verify_password
from bson import ObjectId

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserService:
    """
    用户服务类
    
    提供用户相关的所有业务逻辑操作，包括用户注册、认证、查询等。
    使用静态方法实现，作为应用程序与MongoDB数据库之间的接口层。
    """
    
    @staticmethod
    async def get_by_email(email: str) -> Optional[UserInDB]:
        """
        通过邮箱查找用户
        
        在数据库中查询指定邮箱的用户记录。
        
        Args:
            email (str): 用户邮箱地址
            
        Returns:
            Optional[UserInDB]: 找到则返回用户对象，否则返回None
        """
        logger.info(f"尝试通过邮箱查找用户: {email}")
        user = await mongodb.db.users.find_one({"email": email})
        if user:
            logger.info(f"找到用户: {email}")
            return UserInDB(
                id=str(user["_id"]),
                email=user["email"],
                username=user["username"],
                hashed_password=user["hashed_password"],
                is_active=user.get("is_active", True),
                is_superuser=user.get("is_superuser", False),
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )
        logger.info(f"未找到用户: {email}")
        return None

    @staticmethod
    async def get_by_username(username: str) -> Optional[UserInDB]:
        """
        通过用户名查找用户
        
        在数据库中查询指定用户名的用户记录。
        
        Args:
            username (str): 用户名
            
        Returns:
            Optional[UserInDB]: 找到则返回用户对象，否则返回None
        """
        logger.info(f"尝试通过用户名查找用户: {username}")
        user = await mongodb.db.users.find_one({"username": username})
        if user:
            logger.info(f"找到用户: {username}")
            return UserInDB(
                id=str(user["_id"]),
                email=user["email"],
                username=user["username"],
                hashed_password=user["hashed_password"],
                is_active=user.get("is_active", True),
                is_superuser=user.get("is_superuser", False),
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )
        logger.info(f"未找到用户: {username}")
        return None

    @staticmethod
    async def create(user: UserCreate) -> User:
        """
        创建新用户
        
        将用户信息保存到数据库，处理密码哈希等逻辑。
        
        Args:
            user (UserCreate): 包含用户创建所需信息的对象
            
        Returns:
            User: 创建成功的用户对象
            
        Raises:
            Exception: 创建过程中的任何错误
        """
        logger.info(f"开始创建用户: {user.email}, {user.username}")
        try:
            now = datetime.utcnow()
            user_dict = {
                "email": user.email,
                "username": user.username,
                "hashed_password": get_password_hash(user.password),
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": now,
                "updated_at": now
            }
            logger.info(f"准备插入用户数据: {user_dict}")
            result = await mongodb.db.users.insert_one(user_dict)
            logger.info(f"用户创建成功，ID: {result.inserted_id}")
            return User(
                id=str(result.inserted_id),
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=now,
                updated_at=now
            )
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            raise

    @staticmethod
    async def authenticate(username_or_email: str, password: str) -> Optional[User]:
        """
        用户认证
        
        验证用户凭据，支持使用用户名或邮箱进行认证。
        
        Args:
            username_or_email (str): 用户名或邮箱
            password (str): 明文密码
            
        Returns:
            Optional[User]: 验证成功返回用户对象，失败返回None
        """
        logger.info(f"尝试验证用户: {username_or_email}")
        # 尝试作为邮箱查找用户
        user = await UserService.get_by_email(username_or_email)
        if not user:
            # 如果没找到，尝试作为用户名查找用户
            user = await UserService.get_by_username(username_or_email)
            if not user:
                logger.info(f"用户不存在: {username_or_email}")
                return None
        
        if not verify_password(password, user.hashed_password):
            logger.info(f"密码验证失败: {username_or_email}")
            return None
            
        logger.info(f"用户验证成功: {username_or_email}")
        return User(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

# 单例实例，供应用各部分使用
user_service = UserService() 