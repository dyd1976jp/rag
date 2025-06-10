#!/usr/bin/env python
"""
测试API服务器

创建一个简单的FastAPI应用程序，专门用于测试discover-models功能
"""

import uvicorn
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query
from app.services.llm_service import llm_service
from app.api.deps import get_current_user

app = FastAPI(title="测试API服务器")

@app.get("/test/discover-models", response_model=List[Dict[str, Any]])
async def test_discover_models(
    provider: str = Query(..., description="提供商名称，如lmstudio或ollama"),
    url: str = Query(..., description="API URL，例如http://0.0.0.0:1234")
):
    """测试发现模型功能"""
    print("\n" + "="*50)
    print("### 测试端点(/test/discover-models)被调用 ###")
    print(f"请求参数: provider={provider}, url={url}")
    
    try:
        # 修正URL格式
        if url and not url.startswith("http"):
            print(f"URL格式不正确，添加http://前缀: {url}")
            url = "http://" + url
            print(f"修正后的URL: {url}")
        
        print(f"开始调用llm_service.discover_local_models, provider={provider}, url={url}")
        result = await llm_service.discover_local_models(provider, url)
        print(f"discover_local_models返回结果类型: {type(result)}")
        print(f"discover_local_models返回结果长度: {len(result) if result else 0}")
        
        if not result:
            print("discover_local_models返回空结果")
            return []
            
        if isinstance(result, list) and len(result) > 0 and "error" in result[0]:
            error_msg = result[0].get("error", "未知错误")
            print(f"discover_local_models返回错误: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
            
        print(f"返回成功结果，包含{len(result)}个模型")
        print("="*50 + "\n")
        return result
    except HTTPException as he:
        print(f"HTTP异常: {he.detail}, 状态码: {he.status_code}")
        print("="*50 + "\n")
        raise
    except Exception as e:
        print(f"discover_models处理异常: {str(e)}")
        import traceback
        print(f"异常堆栈: {traceback.format_exc()}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"发现模型时出错: {str(e)}")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "测试API服务器已启动"}

if __name__ == "__main__":
    uvicorn.run("test_api_server:app", host="127.0.0.1", port=8001, reload=True) 