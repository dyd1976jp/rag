#!/usr/bin/env python
"""
测试FastAPI路由注册情况
"""
import uvicorn
from typing import Dict, Any, List
from fastapi import FastAPI, APIRouter, Depends, Query, HTTPException
from app.services.llm_service import llm_service
from app.api.deps import get_current_user

app = FastAPI(title="路由测试")

# 创建一个路由器并注册一些路由
router = APIRouter(prefix="/api/v1/llm")

@router.get("/test-path", response_model=Dict[str, Any])
async def test_path():
    """测试路径"""
    return {"message": "测试路径正常"}

@router.get("/discover-models", response_model=List[Dict[str, Any]])
async def discover_models_new(
    provider: str = Query(..., description="提供商名称"),
    url: str = Query(..., description="API URL"),
):
    """发现模型测试路由"""
    result = await llm_service.discover_local_models(provider, url)
    return result

# 注册路由器到应用程序
app.include_router(router)

@app.get("/")
async def root():
    """根路径"""
    # 获取所有路由信息
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "name": route.name if hasattr(route, "name") else None,
                "methods": route.methods if hasattr(route, "methods") else None
            })
    
    # 检查特定路由是否存在
    discover_models_path = None
    try:
        discover_models_path = app.url_path_for("discover_models_new", provider="test", url="test")
    except Exception as e:
        discover_models_path = f"错误: {str(e)}"
    
    return {
        "message": "路由测试应用已启动",
        "routes": routes,
        "discover_models_path": discover_models_path
    }

if __name__ == "__main__":
    uvicorn.run("test_route:app", host="127.0.0.1", port=8002, reload=True) 