"""
管理员认证API端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta

from app.admin.auth import (
    Token, AdminBase, authenticate_admin, 
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_admin_user
)

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """获取访问令牌"""
    admin = authenticate_admin(form_data.username, form_data.password)
    if not admin:
        logger.warning(f"管理员登录失败: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"管理员登录成功: {admin.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=AdminBase)
async def read_users_me(current_admin: AdminBase = Depends(get_admin_user)):
    """获取当前管理员信息"""
    return current_admin 