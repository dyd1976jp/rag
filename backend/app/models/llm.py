from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

# 定义模型类别
ModelCategory = Literal["chat", "embedding", "other"]

class LLM(BaseModel):
    """大语言模型数据模型"""
    id: Optional[str] = None
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商，如OpenAI、Local等")
    model_type: str = Field(..., description="模型类型，如GPT-3.5、LLaMA等")
    model_category: ModelCategory = Field("chat", description="模型类别: chat, embedding, other")
    api_url: str = Field(..., description="API URL")
    api_key: Optional[str] = Field(None, description="API密钥")
    default: bool = Field(False, description="是否为默认模型")
    context_window: int = Field(4096, description="上下文窗口大小")
    max_output_tokens: int = Field(1000, description="最大输出token数")
    temperature: float = Field(0.7, description="温度参数")
    top_p: float = Field(1.0, description="Top-p（nucleus sampling）参数")
    frequency_penalty: float = Field(0.0, description="频率惩罚参数")
    presence_penalty: float = Field(0.0, description="存在惩罚参数")
    status: str = Field("active", description="模型状态：active, disabled")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = Field(None, description="模型描述")
    capabilities: List[str] = Field(default_factory=list, description="模型能力标签")
    config: Dict[str, Any] = Field(default_factory=dict, description="额外配置参数")
    timeout: int = Field(30, description="API请求超时时间（秒）")
    
    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    } 