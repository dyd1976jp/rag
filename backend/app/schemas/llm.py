from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# 定义模型类别
ModelCategory = Literal["chat", "embedding", "other"]

class LLMBase(BaseModel):
    """基础LLM模型Schema"""
    name: str
    provider: str
    model_type: str
    model_category: ModelCategory = "chat"
    api_url: str
    default: bool = False
    context_window: int = 4096
    max_output_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    description: Optional[str] = None
    capabilities: List[str] = []
    config: Dict[str, Any] = {}
    timeout: int = 30
    
    model_config = ConfigDict(
        protected_namespaces=()
    )

class LLMCreate(LLMBase):
    """创建LLM请求Schema"""
    api_key: Optional[str] = None

class LLMUpdate(BaseModel):
    """更新LLM请求Schema"""
    name: Optional[str] = None
    provider: Optional[str] = None
    model_type: Optional[str] = None
    model_category: Optional[ModelCategory] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    default: Optional[bool] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    
    model_config = ConfigDict(
        protected_namespaces=()
    )

class LLMInDB(LLMBase):
    """数据库中的LLM Schema"""
    id: str
    api_key: Optional[str] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=()
    )

class LLMResponse(LLMBase):
    """LLM响应Schema"""
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=()
    )

class LLMTest(BaseModel):
    """LLM测试请求Schema"""
    llm_id: str
    prompt: str = "您好，请问您是谁？"
    
    model_config = ConfigDict(
        protected_namespaces=()
    )
    
class ProviderInfo(BaseModel):
    """提供商信息Schema"""
    id: str
    name: str
    models_count: int
    
    model_config = ConfigDict(
        protected_namespaces=()
    )
    
class ModelInfo(BaseModel):
    """模型信息Schema"""
    id: str
    name: str
    context_window: int
    
    model_config = ConfigDict(
        protected_namespaces=()
    )