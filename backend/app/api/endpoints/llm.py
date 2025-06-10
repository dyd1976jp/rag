from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from ...schemas.llm import LLMCreate, LLMResponse, LLMUpdate, LLMTest
from ...services.llm_service import llm_service
from ..deps import get_current_user
from ...core.config import settings

router = APIRouter()

@router.post("/", response_model=LLMResponse, status_code=201)
async def create_llm(llm: LLMCreate, current_user = Depends(get_current_user)):
    """
    创建新的LLM模型配置
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = await llm_service.create_llm(llm)
    return result

@router.get("/", response_model=List[LLMResponse])
async def get_llms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    获取所有LLM模型配置
    """
    print(f"调用 get_llms API: skip={skip}, limit={limit}")
    result = await llm_service.get_llms(skip, limit)
    print(f"返回 {len(result)} 个LLM模型")
    return result

@router.get("/default", response_model=LLMResponse)
async def get_default_llm():
    """
    获取默认LLM模型配置
    """
    llm = await llm_service.get_default_llm()
    if not llm:
        raise HTTPException(status_code=404, detail="没有找到默认模型")
    return llm

@router.get("/{llm_id}", response_model=LLMResponse)
async def get_llm(
    llm_id: str = Path(..., title="LLM ID")
):
    """
    获取特定LLM模型配置
    """
    llm = await llm_service.get_llm(llm_id)
    if not llm:
        raise HTTPException(status_code=404, detail="模型不存在")
    return llm

@router.put("/{llm_id}", response_model=LLMResponse)
async def update_llm(
    llm_update: LLMUpdate,
    llm_id: str = Path(..., title="LLM ID"),
    current_user = Depends(get_current_user)
):
    """
    更新LLM模型配置
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    llm = await llm_service.update_llm(llm_id, llm_update)
    if not llm:
        raise HTTPException(status_code=404, detail="模型不存在")
    return llm

@router.delete("/{llm_id}", status_code=204)
async def delete_llm(
    llm_id: str = Path(..., title="LLM ID"),
    current_user = Depends(get_current_user)
):
    """
    删除LLM模型配置
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = await llm_service.delete_llm(llm_id)
    if not result:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"success": True}

@router.post("/test", status_code=200)
async def test_llm(
    test_request: LLMTest,
    current_user = Depends(get_current_user)
):
    """
    测试LLM模型
    """
    result = await llm_service.test_llm(test_request.llm_id, test_request.prompt)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result 

@router.get("/discover", response_model=List[Dict[str, Any]])
async def discover_models(
    provider: str = Query(..., description="提供商名称，如lmstudio或ollama"),
    url: str = Query(..., description="API URL，例如http://0.0.0.0:1234"),
    current_user = Depends(get_current_user)
):
    """
    发现本地服务（如LM Studio或Ollama）中的模型
    
    此接口用于自动发现本地运行的模型服务中的可用模型，
    并检查它们是否已在系统中注册。
    """
    print(f"### 旧版本(endpoints)discover_models被调用 ###")
    print(f"请求参数: provider={provider}, url={url}")
    print(f"当前用户: {current_user.username if current_user else 'None'}")
    
    # 在生产模式下检查权限
    if settings.ENVIRONMENT != "development" and not current_user.is_superuser:
        print(f"用户 {current_user.username} 权限不足，需要管理员权限")
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        print(f"开始调用llm_service.discover_local_models, provider={provider}, url={url}")
        result = await llm_service.discover_local_models(provider, url)
        print(f"discover_local_models返回结果长度: {len(result) if result else 0}")
        
        if not result:
            print("discover_local_models返回空结果")
            return []
            
        if isinstance(result, list) and len(result) > 0 and "error" in result[0]:
            error_msg = result[0].get("error", "未知错误")
            print(f"discover_local_models返回错误: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
            
        return result
    except Exception as e:
        print(f"discover_models处理异常: {str(e)}")
        import traceback
        print(f"异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"发现模型时出错: {str(e)}")

@router.post("/register-from-discovery", response_model=LLMResponse)
async def register_model_from_discovery(
    llm_model_id: str = Body(..., embed=True, description="模型ID"),
    provider: str = Body(..., embed=True, description="提供商名称"),
    name: str = Body(..., embed=True, description="显示名称"),
    api_url: str = Body(..., embed=True, description="API URL"),
    description: Optional[str] = Body(None, embed=True, description="模型描述"),
    context_window: int = Body(8192, embed=True, description="上下文窗口大小"),
    set_as_default: bool = Body(False, embed=True, description="是否设置为默认模型"),
    current_user = Depends(get_current_user)
):
    """
    从发现的模型中注册一个模型到系统
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 创建模型配置
    llm_create = LLMCreate(
        name=name,
        provider=provider,
        model_type=llm_model_id,
        api_url=api_url,
        default=set_as_default,
        context_window=context_window,
        max_output_tokens=1000,  # 默认值
        temperature=0.7,         # 默认值
        description=description or f"{provider}提供的{llm_model_id}模型",
        timeout=60 if provider.lower() == "local" else 30
    )
    
    # 调用创建服务
    result = await llm_service.create_llm(llm_create)
    return result