from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, status
from app.schemas.llm import LLMCreate, LLMResponse, LLMUpdate, LLMTest
from app.services.llm_service import llm_service
from app.api.deps import get_current_user
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=LLMResponse, status_code=201)
async def create_llm(llm: LLMCreate, current_user = Depends(get_current_user)):
    """
    创建新的LLM模型配置
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    result = await llm_service.create_llm(llm)
    return result

@router.get("/", response_model=List[LLMResponse])
async def get_llms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    获取所有LLM模型配置
    """
    return await llm_service.get_llms(skip, limit)

@router.get("/default", response_model=LLMResponse)
async def get_default_llm():
    """
    获取默认LLM模型配置
    """
    llm = await llm_service.get_default_llm()
    if not llm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="没有找到默认模型")
    return llm

@router.get("/providers/list", response_model=List[str])
async def list_providers(
    current_user = Depends(get_current_user)
):
    """
    获取所有可用的LLM提供商
    """
    return await llm_service.get_providers()

@router.get("/models/{provider}", response_model=List[Dict[str, Any]])
async def list_models_by_provider(
    provider: str = Path(..., title="提供商名称"),
    current_user = Depends(get_current_user)
):
    """
    获取指定提供商下的所有模型类型
    """
    return await llm_service.get_models_by_provider(provider)

# 修改转发逻辑，直接调用服务层函数
@router.get("/discover-models", response_model=List[Dict[str, Any]])
async def get_discover_models(
    provider: str = Query(..., description="提供商名称，如lmstudio或ollama"),
    url: str = Query(..., description="API URL，例如http://0.0.0.0:1234"),
    current_user = Depends(get_current_user)
):
    """
    发现本地服务中的模型

    此接口用于自动发现本地运行的模型服务中的可用模型，
    并检查它们是否已在系统中注册。

    - provider: 提供商，目前支持"lmstudio"和"ollama"
    - url: 服务的API地址，例如LM Studio为"http://0.0.0.0:1234"
    """
    logger.info(f"发现模型请求: provider={provider}, url={url}")

    try:
        # 修正URL格式
        if url and not url.startswith("http"):
            url = "http://" + url
            logger.debug(f"URL已修正: {url}")

        # 直接调用服务层函数
        result = await llm_service.discover_local_models(provider, url)

        if not result:
            logger.warning(f"未找到模型: provider={provider}, url={url}")
            return []

        if isinstance(result, list) and len(result) > 0 and "error" in result[0]:
            error_msg = result[0].get("error", "未知错误")
            logger.error(f"发现模型错误: {error_msg}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

        logger.info(f"发现{len(result)}个模型")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"处理发现模型请求时出错: {str(e)}")
        return [{"error": f"处理请求时出错: {str(e)}"}]

@router.get("/{llm_id}", response_model=LLMResponse)
async def get_llm(
    llm_id: str = Path(..., title="LLM ID"),
    current_user = Depends(get_current_user)
):
    """
    获取特定LLM模型配置
    """
    llm = await llm_service.get_llm(llm_id)
    if not llm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    llm = await llm_service.update_llm(llm_id, llm_update)
    if not llm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    result = await llm_service.delete_llm(llm_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return None

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result

@router.post("/set-default/{llm_id}", response_model=LLMResponse)
async def set_default_llm(
    llm_id: str = Path(..., title="LLM ID"),
    current_user = Depends(get_current_user)
):
    """
    设置默认LLM模型
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    result = await llm_service.set_default_llm(llm_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return result



# 直接使用服务层方法，保持与discover模块一致的参数
@router.post("/register-from-discovery", response_model=LLMResponse)
async def register_from_discovery(
    llm_model_id: str = Body(..., embed=True, description="模型ID"),
    provider: str = Body(..., embed=True, description="提供商名称"),
    name: str = Body(..., embed=True, description="显示名称"),
    api_url: str = Body(..., embed=True, description="API URL"),
    description: Optional[str] = Body(None, embed=True, description="模型描述"),
    context_window: int = Body(8192, embed=True, description="上下文窗口大小"),
    set_as_default: bool = Body(False, embed=True, description="是否设置为默认模型"),
    max_output_tokens: int = Body(1000, embed=True, description="最大输出token数"),
    temperature: float = Body(0.7, embed=True, description="温度参数"),
    custom_options: Optional[Dict[str, Any]] = Body(None, embed=True, description="自定义选项"),
    current_user = Depends(get_current_user)
):
    """
    从发现的模型中注册一个模型到系统
    
    此接口用于将发现的模型快速注册到系统中，无需手动填写所有参数。
    它使用discover接口返回的模型信息，并允许用户设置一些自定义选项。
    
    Args:
        llm_model_id: 模型ID
        provider: 提供商名称
        name: 显示名称
        api_url: API URL
        description: 模型描述
        context_window: 上下文窗口大小
        set_as_default: 是否设置为默认模型
        max_output_tokens: 最大输出token数
        temperature: 温度参数
        custom_options: 自定义选项
    """
    if not current_user.is_superuser:
        logger.warning(f"非管理员用户尝试注册模型: user_id={current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    # 使用统一的注册方法
    return await llm_service.register_discovered_model(
        model_id=llm_model_id,
        provider=provider,
        name=name,
        api_url=api_url,
        description=description,
        context_window=context_window,
        set_as_default=set_as_default,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        custom_options=custom_options
    ) 