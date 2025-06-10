from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator, constr

class DocumentCollection(BaseModel):
    """文档集模型"""
    id: str = Field(..., description="文档集ID")
    name: str = Field(..., description="文档集名称")
    description: Optional[str] = Field(None, description="文档集描述")
    user_id: str = Field(..., description="创建者ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    document_count: int = Field(default=0, description="文档数量")
    tags: List[str] = Field(default_factory=list, description="标签")

class DocumentCollectionCreate(BaseModel):
    """创建文档集的请求模型"""
    name: constr(min_length=1, max_length=100, strip_whitespace=True) = Field(..., description="文档集名称")
    description: Optional[constr(max_length=500, strip_whitespace=True)] = Field(None, description="文档集描述")
    tags: List[constr(min_length=1, max_length=50, strip_whitespace=True)] = Field(
        default_factory=list,
        max_items=10,
        description="标签列表，每个标签不超过50字符，最多10个标签"
    )

    @validator('tags')
    def validate_tags(cls, v):
        """验证标签列表"""
        # 去重
        v = list(set(v))
        # 移除空标签
        v = [tag for tag in v if tag.strip()]
        return v

    @validator('name')
    def validate_name(cls, v):
        """验证文档集名称"""
        if not v.strip():
            raise ValueError('文档集名称不能为空')
        return v.strip()

class DocumentCollectionUpdate(BaseModel):
    """更新文档集的请求模型"""
    name: Optional[str] = Field(None, description="文档集名称")
    description: Optional[str] = Field(None, description="文档集描述")
    tags: Optional[List[str]] = Field(None, description="标签")

class DocumentCollectionResponse(BaseModel):
    """文档集响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    collection: Optional[DocumentCollection] = Field(None, description="文档集信息")

class DocumentCollectionListResponse(BaseModel):
    """文档集列表响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    collections: List[DocumentCollection] = Field(default_factory=list, description="文档集列表") 