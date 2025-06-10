"""
向量存储管理API端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pymilvus import utility, Collection, connections
from pymilvus.client.types import LoadState

from app.admin.auth import get_admin_user, AdminBase
from app.admin.schemas.admin import (
    VectorCollectionsResponse,
    VectorCollectionStatsResponse
)
from app.rag.vector_store import MilvusVectorStore

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 创建向量存储实例
try:
    vector_store = MilvusVectorStore()
except Exception as e:
    logger.error(f"初始化向量存储失败: {str(e)}")
    vector_store = None

@router.get("/status")
async def check_vector_store_status(admin_user: AdminBase = Depends(get_admin_user)):
    """检查向量存储服务状态"""
    try:
        if not vector_store:
            return {"status": "未初始化", "healthy": False}
            
        connected = connections.has_connection("default")
        if not connected:
            try:
                connections.connect("default", host=vector_store.host, port=vector_store.port)
                connected = True
            except:
                connected = False
                
        return {
            "status": "正常" if connected else "连接失败",
            "healthy": connected,
            "host": vector_store.host,
            "port": vector_store.port
        }
    except Exception as e:
        return {
            "status": "异常",
            "healthy": False,
            "error": str(e)
        }

@router.get("/collections", response_model=VectorCollectionsResponse)
async def list_vector_collections(admin_user: AdminBase = Depends(get_admin_user)):
    """获取所有向量集合"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="向量存储服务未初始化")
            
        # 尝试建立连接
        if not connections.has_connection("default"):
            try:
                connections.connect("default", host=vector_store.host, port=vector_store.port)
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"无法连接到向量存储服务: {str(e)}")
                
        # 测试连接是否有效
        try:
            collections = utility.list_collections()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"向量存储服务连接异常: {str(e)}")
            
        return {"collections": collections}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取向量集合列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections/{collection_name}/stats", response_model=VectorCollectionStatsResponse)
async def get_collection_stats(
    collection_name: str,
    admin_user: AdminBase = Depends(get_admin_user)
):
    """获取向量集合统计信息"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="向量存储服务不可用")
            
        # 确保集合存在
        collections = utility.list_collections()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
            
        # 加载集合
        vector_store.create_collection(collection_name)  # 这会加载集合
        
        # 获取统计信息
        try:
            # 直接使用pymilvus API获取集合信息
            collection = Collection(collection_name)
            if utility.load_state(collection_name) != LoadState.Loaded:
                collection.load()
                
            stats = {
                "collection_name": collection.name,
                "row_count": collection.num_entities,
                "index_info": collection.index().params if collection.has_index() else None,
                "schema": {field.name: str(field.dtype) for field in collection.schema.fields}
            }
            return stats
        except Exception as e:
            logger.error(f"获取集合 {collection_name} 的统计信息失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取集合统计信息失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取向量集合统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取向量集合统计信息失败: {str(e)}")

@router.get("/collections/{collection_name}/sample")
async def get_collection_sample(
    collection_name: str,
    limit: int = Query(10, ge=1, le=100),
    admin_user: AdminBase = Depends(get_admin_user)
):
    """获取向量集合样本数据"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="向量存储服务不可用")
            
        # 确保集合存在
        collections = utility.list_collections()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
            
        # 加载集合并获取样本
        collection = Collection(collection_name)
        if utility.load_state(collection_name) != LoadState.Loaded:
            collection.load()
            
        # 获取记录总数
        row_count = collection.num_entities
        
        # 如果没有数据，返回空
        if row_count == 0:
            return {
                "collection": collection_name,
                "total_count": 0,
                "sample_count": 0,
                "samples": []
            }
        
        # 获取样本
        samples = collection.query(
            expr="",  # 空表达式匹配所有
            output_fields=["id", "metadata"],
            limit=limit
        )
        
        return {
            "collection": collection_name,
            "total_count": row_count,
            "sample_count": len(samples),
            "samples": samples
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取向量集合样本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取向量集合样本失败: {str(e)}")

@router.post("/collections/{collection_name}/flush")
async def flush_collection(
    collection_name: str,
    admin_user: AdminBase = Depends(get_admin_user)
):
    """强制刷新集合（将内存中的数据写入磁盘）"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="向量存储服务不可用")
            
        # 确保集合存在
        collections = utility.list_collections()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
            
        # 刷新集合
        collection = Collection(collection_name)
        collection.flush()
        
        # 记录操作日志
        logger.info(f"管理员 {admin_user.username} 刷新了向量集合 {collection_name}")
        
        return {
            "success": True,
            "message": f"集合 {collection_name} 刷新成功"
        }
    except Exception as e:
        logger.error(f"刷新向量集合失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新向量集合失败: {str(e)}")

@router.delete("/collections/{collection_name}/purge")
async def purge_collection(
    collection_name: str,
    admin_user: AdminBase = Depends(get_admin_user)
):
    """清空集合中的所有数据（危险操作）"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="向量存储服务不可用")
            
        # 确保集合存在
        collections = utility.list_collections()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
            
        # 获取集合
        collection = Collection(collection_name)
        
        # 删除所有实体（通过表达式匹配所有）
        expr = "id != ''"  # 这将匹配所有非空ID
        
        # 获取删除前的记录数
        before_count = collection.num_entities
        
        # 执行删除
        collection.delete(expr)
        collection.flush()  # 确保删除生效
        
        # 获取删除后的记录数
        after_count = collection.num_entities
        deleted_count = before_count - after_count
        
        # 记录操作日志
        logger.warning(f"管理员 {admin_user.username} 清空了向量集合 {collection_name}，删除了 {deleted_count} 条记录")
        
        return {
            "success": True,
            "message": f"集合 {collection_name} 已清空",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"清空向量集合失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空向量集合失败: {str(e)}") 