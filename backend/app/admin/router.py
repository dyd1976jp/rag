"""
管理模块的路由配置
"""
from fastapi import APIRouter
from app.admin.endpoints import auth, mongodb_admin, vector_admin, system_admin

# 创建管理模块路由器
router = APIRouter(
    prefix="/admin/api",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

# 添加认证路由
router.include_router(auth.router, prefix="/auth", tags=["admin.auth"])

# 添加MongoDB管理路由
router.include_router(mongodb_admin.router, prefix="/mongodb", tags=["admin.mongodb"])

# 添加向量存储管理路由
router.include_router(vector_admin.router, prefix="/vector", tags=["admin.vector"])

# 添加系统监控路由
router.include_router(system_admin.router, prefix="/system", tags=["admin.system"]) 