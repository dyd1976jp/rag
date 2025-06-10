"""
MongoDB管理API端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorCollection

from app.admin.auth import get_admin_user, AdminBase
from app.admin.schemas.admin import (
    MongoDBCollectionsResponse,
    MongoDBCollectionResponse,
    DocumentUpdateRequest,
    DocumentDeleteRequest,
    DocumentInsertRequest
)
from app.db.mongodb import mongodb

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/collections", response_model=MongoDBCollectionsResponse)
async def list_collections(admin_user: AdminBase = Depends(get_admin_user)):
    """获取所有集合列表"""
    try:
        collections = await mongodb.db.list_collection_names()
        return {"collections": collections}
    except Exception as e:
        logger.error(f"获取集合列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取集合列表失败: {str(e)}")

@router.get("/collections/{collection_name}", response_model=MongoDBCollectionResponse)
async def get_collection_data(
    collection_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filter: Optional[str] = Query(None, description="JSON格式的过滤条件"),
    sort_field: Optional[str] = Query(None, description="排序字段"),
    sort_order: int = Query(1, ge=-1, le=1, description="排序顺序：1升序，-1降序"),
    admin_user: AdminBase = Depends(get_admin_user)
):
    """获取集合数据"""
    try:
        # 验证集合存在
        collections = await mongodb.db.list_collection_names()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
        
        # 构建查询条件
        query_filter = {}
        if filter:
            import json
            try:
                query_filter = json.loads(filter)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="过滤条件格式无效，必须是有效的JSON")
        
        # 获取文档总数
        count = await mongodb.db[collection_name].count_documents(query_filter)
        
        # 构建排序条件
        sort_options = None
        if sort_field:
            sort_options = [(sort_field, sort_order)]
        
        # 查询文档
        cursor = mongodb.db[collection_name].find(query_filter)
        
        # 应用排序
        if sort_options:
            cursor = cursor.sort(sort_options)
        
        # 应用分页
        cursor = cursor.skip(skip).limit(limit)
        
        # 获取结果
        documents = []
        async for doc in cursor:
            # 处理ObjectId
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
            
        return {
            "collection": collection_name,
            "total_documents": count,
            "documents": documents,
            "pagination": {
                "skip": skip,
                "limit": limit
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取集合 {collection_name} 数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取集合数据失败: {str(e)}")

@router.post("/collections/{collection_name}/documents")
async def insert_document(
    collection_name: str,
    document_data: DocumentInsertRequest,
    admin_user: AdminBase = Depends(get_admin_user)
):
    """向集合中插入文档"""
    try:
        # 验证集合存在
        collections = await mongodb.db.list_collection_names()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
        
        # 插入文档
        result = await mongodb.db[collection_name].insert_one(document_data.document)
        
        # 记录操作日志
        logger.info(f"管理员 {admin_user.username} 向集合 {collection_name} 插入文档")
        
        return {
            "success": True,
            "message": "文档插入成功",
            "inserted_id": str(result.inserted_id)
        }
    except Exception as e:
        logger.error(f"插入文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"插入文档失败: {str(e)}")

@router.put("/collections/{collection_name}/documents")
async def update_documents(
    collection_name: str,
    update_data: DocumentUpdateRequest,
    admin_user: AdminBase = Depends(get_admin_user)
):
    """更新集合中的文档"""
    try:
        # 验证集合存在
        collections = await mongodb.db.list_collection_names()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
        
        # 更新文档
        result = await mongodb.db[collection_name].update_many(
            update_data.query,
            update_data.update
        )
        
        # 记录操作日志
        logger.info(f"管理员 {admin_user.username} 更新了集合 {collection_name} 中的 {result.modified_count} 个文档")
        
        return {
            "success": True,
            "message": f"文档更新成功",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }
    except Exception as e:
        logger.error(f"更新文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新文档失败: {str(e)}")

@router.delete("/collections/{collection_name}/documents")
async def delete_documents(
    collection_name: str,
    delete_data: DocumentDeleteRequest,
    admin_user: AdminBase = Depends(get_admin_user)
):
    """删除集合中的文档"""
    try:
        # 验证集合存在
        collections = await mongodb.db.list_collection_names()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
        
        # 删除文档
        result = await mongodb.db[collection_name].delete_many(delete_data.query)
        
        # 记录操作日志
        logger.info(f"管理员 {admin_user.username} 从集合 {collection_name} 中删除了 {result.deleted_count} 个文档")
        
        return {
            "success": True,
            "message": f"文档删除成功",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}") 