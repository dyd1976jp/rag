"""
模型发现API端点

这个模块专门处理模型发现功能的API端点
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from app.services.llm_service import llm_service
from app.api.deps import get_current_user
from app.schemas.llm import LLMCreate, LLMResponse
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def discover_models(
    provider: str = Query(..., description="提供商名称，如lmstudio或ollama"),
    url: str = Query(..., description="API URL，例如http://0.0.0.0:1234"),
    current_user = Depends(get_current_user)
):
    """
    发现本地服务（如LM Studio或Ollama）中的模型
    
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
        
        # 调用服务层函数
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

@router.post("/register", response_model=LLMResponse)
async def register_model(
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
    logger.info(f"注册模型请求: model_id={llm_model_id}, provider={provider}, name={name}")
    
    try:
        if not current_user.is_superuser:
            logger.warning(f"非管理员用户尝试注册模型: user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        
        # 使用统一的注册方法
        result = await llm_service.register_discovered_model(
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
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"注册模型时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"注册模型时出错: {str(e)}") 