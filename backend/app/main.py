"""
应用程序主入口模块

本模块是FastAPI应用的主入口点，负责:
1. 应用程序初始化与配置
2. 数据库连接的生命周期管理
3. 中间件配置（CORS等）
4. API路由注册
5. 健康检查端点提供
"""

import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .api.endpoints import auth, llm as llm_old
from .api.v1.api import api_v1_router
from .admin.router import router as admin_router
from .db.mongodb import mongodb

# 创建日志目录
os.makedirs("logs", exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理器
    
    负责在应用启动时初始化必要的资源，在应用关闭时清理资源。
    """
    # 启动时执行的操作
    try:
        # 连接数据库
        logger.info("正在连接到MongoDB...")
        await mongodb.connect()
        logger.info("MongoDB连接成功")
        
        # 初始化RAG服务
        from app.rag import initialize_rag
        logger.info("正在初始化RAG服务...")
        await initialize_rag()
        logger.info("RAG服务初始化完成")
        
        # 初始化RAG服务的MongoDB索引
        from app.services.rag_service import rag_service
        logger.info("正在初始化RAG服务索引...")
        await rag_service.setup_indexes()
        logger.info("RAG服务索引初始化完成")
        
        yield
    finally:
        # 关闭时执行的操作
        logger.info("正在关闭MongoDB连接...")
        await mongodb.close()
        logger.info("MongoDB连接已关闭")

app = FastAPI(
    title="RAG Chat API",
    description="基于 RAG 的智能问答系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 注册路由
logger.info(f"注册认证路由: {settings.API_V1_STR}/auth")
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])

# 注册旧版LLM路由 - 注释掉这行，防止路由冲突
# app.include_router(llm_old.router, prefix=f"{settings.API_V1_STR}/llm", tags=["大语言模型-旧版"])

# 注册v1 API路由
logger.info(f"注册API v1路由: {settings.API_V1_STR}")
app.include_router(api_v1_router, prefix="/api/v1")

# 注册管理模块路由
logger.info("注册管理模块路由: /admin/api")
app.include_router(admin_router)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后再试"}
    )

@app.get("/")
async def root():
    """
    API根端点
    
    提供简单的健康检查和API欢迎信息。
    
    Returns:
        dict: 包含欢迎信息的字典
    """
    return {"message": "Welcome to RAG Chat API"}

# 启动时记录
@app.on_event("startup")
async def startup_event():
    logger.info("应用启动")

# 关闭时记录
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用关闭") 