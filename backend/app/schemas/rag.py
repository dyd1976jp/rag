from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentOverview(BaseModel):
    """文档概览信息"""
    title: str = Field(default="未命名文档", description="文档标题")
    total_length: int = Field(..., description="文档总长度")
    total_segments: int = Field(..., description="总段落数")
    parent_segments: int = Field(..., description="父段落数")
    child_segments: int = Field(..., description="子段落数")

class SegmentInfo(BaseModel):
    """段落信息"""
    id: int = Field(..., description="段落ID")
    content: str = Field(..., description="段落内容")
    start: int = Field(..., description="开始位置")
    end: int = Field(..., description="结束位置")
    length: int = Field(..., description="段落长度")
    type: str = Field(..., description="段落类型(parent/child)")
    children: List[Dict[str, Any]] = Field(default_factory=list, description="子段落列表")

class DocumentUploadResponse(BaseModel):
    """统一的文档上传响应格式，支持预览模式和正式上传模式"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    preview_mode: bool = Field(..., description="是否为预览模式")
    doc_id: str = Field(..., description="文档ID")

    # 统计信息
    total_segments: int = Field(..., description="总段落数")
    parent_segments: int = Field(..., description="父段落数")
    child_segments: int = Field(..., description="子段落数")

    # 详细内容
    parentContent: str = Field(..., description="完整文档内容")
    childrenContent: List[str] = Field(default_factory=list, description="所有子块内容列表")
    segments: List[SegmentInfo] = Field(default_factory=list, description="层级结构的段落数组")

    # 文档概览
    document_overview: DocumentOverview = Field(..., description="文档概览信息")

    # 可选字段（仅在正式上传模式下使用）
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")

class DocumentSearchRequest(BaseModel):
    query: str = Field(..., description="搜索查询文本")
    top_k: int = Field(3, description="返回结果数量")
    search_all: bool = Field(False, description="是否搜索所有用户的文档，默认只搜索当前用户的文档")
    include_parent: bool = Field(False, description="是否包含父文档，默认不包含")
    collection_id: Optional[str] = Field(None, description="文档集ID，如果指定则只搜索该文档集中的文档")

class DocumentMetadata(BaseModel):
    doc_id: Optional[str] = None
    document_id: Optional[str] = None
    file_name: Optional[str] = None
    position: Optional[int] = None
    score: Optional[float] = None

class DocumentResult(BaseModel):
    content: str
    metadata: DocumentMetadata

class DocumentSearchResponse(BaseModel):
    success: bool
    message: str
    results: List[DocumentResult] = []

class DocumentListItem(BaseModel):
    id: str
    file_name: str
    user_id: str
    segments_count: int
    created_at: datetime
    status: str

class DocumentListResponse(BaseModel):
    documents: List[DocumentListItem]

class DeleteDocumentResponse(BaseModel):
    success: bool
    message: str
    deleted_segments: Optional[int] = Field(0, description="删除的段落数量")
    deleted_document: Optional[bool] = Field(False, description="是否成功删除文档")
    warning: Optional[str] = Field(None, description="删除过程中的警告信息")
    error_code: Optional[str] = Field(None, description="错误代码，用于前端错误处理")
    document_name: Optional[str] = Field(None, description="被删除的文档名称")

class RAGChatRequest(BaseModel):
    query: str = Field(..., description="用户查询")
    conversation_id: Optional[str] = Field(None, description="对话ID，新对话可不传")
    enable_rag: bool = Field(True, description="是否启用RAG")
    top_k: int = Field(3, description="检索结果数量")
    collection_id: Optional[str] = Field(None, description="文档集ID，如果指定则只在该文档集中搜索")

class RAGSource(BaseModel):
    content: str
    file_name: str
    score: Optional[float] = None

class RAGChatResponse(BaseModel):
    success: bool
    message: str
    response: str
    sources: List[RAGSource] = []
    conversation_id: str
    error_code: Optional[str] = Field(None, description="错误代码，用于前端错误处理")

class RAGStatusResponse(BaseModel):
    available: bool = Field(..., description="服务是否可用")
    message: str = Field(..., description="状态消息")
    status: Dict[str, bool] = Field(..., description="各组件状态")
    server_info: Dict[str, Any] = Field(default_factory=dict, description="服务器信息")

class DocumentResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    document: Optional[Dict[str, Any]] = None

class DocumentSlicePreviewRequest(BaseModel):
    doc_id: str = Field(..., description="文档ID")
    slice_index: int = Field(..., description="切割索引位置")

class DocumentSlicePreviewResponse(BaseModel):
    success: bool
    message: str
    parentContent: Optional[str] = Field(None, description="父切割内容")
    childrenContent: List[str] = Field(default_factory=list, description="子切割列表内容")
    segments: List[SegmentInfo] = Field(default_factory=list, description="所有段落信息")
    total_segments: int = Field(0, description="总段落数")