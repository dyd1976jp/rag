"""
认证API端点模块

本模块定义了与用户认证相关的API端点，包括：
1. 用户注册
2. 用户登录与JWT令牌生成
3. 认证错误处理

作为前端应用与后端用户服务之间的接口层，处理HTTP请求并返回适当的响应。
"""

from datetime import timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ...core.security import create_access_token
from ...core.config import settings
from ...services.user import user_service
from ...models.user import UserCreate, User

# 设置日志
logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter()

@router.post("/register", response_model=User)
async def register(user: UserCreate):
    """
    用户注册接口
    
    处理新用户注册请求，验证邮箱和用户名唯一性，创建新用户账户。
    
    Args:
        user (UserCreate): 用户注册信息，包含邮箱、用户名、密码等
        
    Returns:
        User: 创建成功的用户信息(不含密码)
        
    Raises:
        HTTPException: 
            - 400: 邮箱已被注册
            - 400: 用户名已被占用
            - 500: 服务器内部错误
    """
    logger.info(f"收到注册请求: {user.email}, {user.username}")
    try:
        db_user = await user_service.get_by_email(user.email)
        if db_user:
            logger.warning(f"邮箱已注册: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        db_user = await user_service.get_by_username(user.username)
        if db_user:
            logger.warning(f"用户名已被占用: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        logger.info(f"开始创建用户: {user.email}")
        result = await user_service.create(user)
        logger.info(f"用户创建成功: {user.email}")
        return result
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    用户登录接口
    
    验证用户凭据，生成并返回JWT访问令牌。
    
    Args:
        form_data (OAuth2PasswordRequestForm): 包含用户名/邮箱和密码的表单数据
        
    Returns:
        dict: 包含访问令牌、令牌类型和用户信息的字典
        
    Raises:
        HTTPException:
            - 401: 用户名或密码错误
            - 500: 服务器内部错误
    """
    logger.info(f"收到登录请求: {form_data.username}")
    try:
        user = await user_service.authenticate(form_data.username, form_data.password)
        if not user:
            logger.warning(f"登录失败，用户名或密码错误: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        logger.info(f"用户登录成功: {user.email}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        ) 