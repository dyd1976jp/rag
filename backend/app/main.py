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
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from .core.config import settings
from .api.endpoints import auth, llm as llm_old
from .api.v1.api import api_v1_router
from .admin.router import router as admin_router
from .db.mongodb import mongodb
from .core.paths import LOGS_DIR, APP_LOGS_DIR

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(APP_LOGS_DIR / "app.log")),
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

# 请求验证异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    请求验证异常处理器

    专门处理RequestValidationError，避免在处理包含二进制数据的multipart/form-data请求时出现UTF-8编码错误。

    Args:
        request: FastAPI请求对象
        exc: 请求验证异常对象

    Returns:
        JSONResponse: 统一的错误响应
    """
    try:
        # 安全地提取错误信息，避免编码问题
        error_details = []
        for error in exc.errors():
            # 只提取安全的字符串信息，避免包含二进制数据
            safe_error = {
                "type": error.get("type", "validation_error"),
                "loc": [str(loc) for loc in error.get("loc", [])],
                "msg": str(error.get("msg", "Validation error"))
            }
            error_details.append(safe_error)

        logger.warning(f"请求验证失败: {request.url} - {len(error_details)}个错误")

        # 检查是否是文件上传相关的错误
        url_path = str(request.url.path)
        if "upload" in url_path or "preview-split" in url_path:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "文件上传请求格式错误。请确保使用正确的端点：使用 /documents/upload 端点上传文件，并设置 preview_only=true 进行预览。",
                    "error_type": "file_upload_validation_error",
                    "suggestion": "对于文档预览分割，请使用 POST /api/v1/rag/documents/upload 端点，并在表单数据中设置 preview_only=true"
                }
            )

        return JSONResponse(
            status_code=422,
            content={
                "detail": "请求参数验证失败",
                "errors": error_details
            }
        )
    except Exception as e:
        # 如果在处理验证错误时出现异常，返回简单的错误信息
        logger.error(f"处理验证异常时出错: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": "请求格式错误，请检查请求参数"}
        )

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器

    捕获所有未处理的异常，记录日志并返回统一的错误响应。

    Args:
        request: FastAPI请求对象
        exc: 异常对象

    Returns:
        JSONResponse: 统一的错误响应
    """
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
async def startup_event() -> None:
    """
    应用启动事件处理器

    在应用启动时执行初始化操作和记录日志。
    """
    logger.info("应用启动")

# 关闭时记录
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    应用关闭事件处理器

    在应用关闭时执行清理操作和记录日志。
    """
    logger.info("应用关闭")