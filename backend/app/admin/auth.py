"""
管理员认证模块
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel
import os

# 配置
SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev_secret_key_for_rag_admin_please_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ADMIN_TOKEN_EXPIRE_MINUTES", "30"))

# 密码处理
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/api/token")

# 模型
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class AdminBase(BaseModel):
    username: str
    email: Optional[str] = None
    is_active: bool = True

class AdminInDB(AdminBase):
    hashed_password: str

# 简单的管理员列表，实际应用中应该存储在数据库中
admins_db = {
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": pwd_context.hash("adminpassword"),  # 在实际应用中应该更安全
        "is_active": True
    }
}

def verify_password(plain_password, hashed_password):
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """生成密码哈希"""
    return pwd_context.hash(password)

def get_admin(username: str):
    """根据用户名获取管理员信息"""
    if username in admins_db:
        admin_dict = admins_db[username]
        return AdminInDB(**admin_dict)
    return None

def authenticate_admin(username: str, password: str):
    """验证管理员凭据"""
    admin = get_admin(username)
    if not admin:
        return False
    if not verify_password(password, admin.hashed_password):
        return False
    return admin

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_admin(token: str = Depends(oauth2_scheme)):
    """获取当前管理员"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    admin = get_admin(username=token_data.username)
    if admin is None:
        raise credentials_exception
    
    if not admin.is_active:
        raise HTTPException(status_code=400, detail="管理员账户已停用")
    
    return AdminBase(username=admin.username, email=admin.email, is_active=admin.is_active)

async def get_admin_user(admin: AdminBase = Depends(get_current_admin)):
    """依赖项：获取已认证的管理员"""
    return admin 