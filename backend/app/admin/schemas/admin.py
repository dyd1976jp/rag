"""
管理模块的数据模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# MongoDB管理相关模型
class CollectionInfo(BaseModel):
    name: str
    document_count: int
    size: Optional[int] = None
    
class DocumentItem(BaseModel):
    id: str
    data: Dict[str, Any]
    
class MongoDBCollectionResponse(BaseModel):
    collection: str
    total_documents: int
    documents: List[Dict[str, Any]]
    pagination: Dict[str, int]
    
class MongoDBCollectionsResponse(BaseModel):
    collections: List[str]
    
class DocumentUpdateRequest(BaseModel):
    query: Dict[str, Any] = Field(..., description="查询条件")
    update: Dict[str, Any] = Field(..., description="更新内容")
    
class DocumentDeleteRequest(BaseModel):
    query: Dict[str, Any] = Field(..., description="查询条件")
    
class DocumentInsertRequest(BaseModel):
    document: Dict[str, Any] = Field(..., description="要插入的文档")
    
# 向量存储管理相关模型
class VectorCollectionInfo(BaseModel):
    name: str
    entity_count: int
    
class VectorCollectionsResponse(BaseModel):
    collections: List[str]
    
class VectorCollectionStatsResponse(BaseModel):
    collection_name: str
    row_count: int
    index_info: Optional[Dict[str, Any]] = None
    schema: Optional[Dict[str, str]] = None
    
# 系统监控相关模型
class CPUMetrics(BaseModel):
    percent: float
    cores: int
    
class MemoryMetrics(BaseModel):
    total: int
    available: int
    used: int
    percent: float
    
class DiskMetrics(BaseModel):
    total: int
    used: int
    free: int
    percent: float
    
class GPUMetrics(BaseModel):
    name: Optional[str] = None
    percent: Optional[float] = None
    memory_total: Optional[int] = None
    memory_used: Optional[int] = None
    memory_free: Optional[int] = None
    memory_percent: Optional[float] = None
    
class SystemMetricsResponse(BaseModel):
    cpu: CPUMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    gpu: Optional[GPUMetrics] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
# 管理日志相关模型
class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    admin: Optional[str] = None
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    pagination: Dict[str, int] 