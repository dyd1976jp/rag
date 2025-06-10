from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2
from jose import JWTError, jwt
from pydantic import ValidationError
from app.core.config import settings
from app.services.user import user_service
from app.models.user import User
from typing import Optional
from datetime import datetime, timezone

# 创建一个在开发模式下不强制认证的OAuth2方案
class OptionalOAuth2(OAuth2):
    """
    可选的OAuth2认证方案，在开发模式下不强制认证
    """
    async def __call__(self, request: Request) -> Optional[str]:
        if settings.ENVIRONMENT == "development":
            return None
        return await super().__call__(request)

# 使用条件认证方案
if settings.ENVIRONMENT == "development":
    print("开发模式: 认证检查已禁用")
    oauth2_scheme = OptionalOAuth2(auto_error=False)
else:
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=True)

# 开发模式下的测试用户邮箱
DEV_TEST_EMAIL = "test@example.com"

async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    从JWT令牌中获取当前用户
    
    验证访问令牌并从中获取用户信息
    
    Args:
        token (str): Bearer令牌
        
    Returns:
        User: 当前登录的用户对象
        
    Raises:
        HTTPException: 当令牌无效或用户不存在时
    """
    # 开发模式下，如果没有token，返回测试用户
    if settings.ENVIRONMENT == "development" and not token:
        print(f"开发模式: 返回测试超级用户")
        current_time = datetime.now(timezone.utc)
        return User(
            email=DEV_TEST_EMAIL,
            username="Test Admin",
            is_active=True,
            is_superuser=True,
            is_admin=True,
            id="dev-test-admin-id",
            created_at=current_time,
            updated_at=current_time
        )
    
    # 处理JWT token
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的身份凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            print("令牌中没有'sub'声明")
            raise credentials_exception
        
        print(f"从令牌解析用户邮箱: {email}")
    except JWTError as e:
        print(f"JWT解码错误: {str(e)}")
        raise credentials_exception
    
    try:
        user = await user_service.get_by_email(email)
        if user is None:
            print(f"找不到邮箱为 {email} 的用户")
            raise credentials_exception
        
        if not user.is_active:
            print(f"用户 {email} 未激活")
            raise HTTPException(status_code=403, detail="用户未激活")
            
        print(f"成功获取用户: {user.username}，是否管理员: {user.is_superuser}")
        return user
    except Exception as e:
        print(f"获取用户时发生错误: {str(e)}")
        import traceback
        print(f"异常堆栈: {traceback.format_exc()}")
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    验证当前用户是否激活
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user

async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    验证当前用户是否为超级用户
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user 