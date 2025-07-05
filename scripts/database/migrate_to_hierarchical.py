#!/usr/bin/env python3
"""
数据库迁移脚本：从传统RAG架构迁移到层次化RAG架构

本脚本将：
1. 创建新的层次化存储集合和索引
2. 提供数据迁移选项（可选）
3. 验证迁移结果

使用方法:
python scripts/database/migrate_to_hierarchical.py [options]
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.db.mongodb import mongodb
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HierarchicalMigrator:
    """层次化架构迁移器"""
    
    def __init__(self):
        self.collections = {
            "documents": "documents",
            "document_segments": "document_segments", 
            "child_chunks": "child_chunks",
            "document_collections": "document_collections"
        }
    
    async def connect_db(self):
        """连接数据库"""
        try:
            await mongodb.connect()
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise
    
    async def create_hierarchical_collections(self):
        """创建层次化存储的集合和索引"""
        try:
            logger.info("开始创建层次化存储的集合和索引...")
            
            # 1. 创建父段落集合的索引
            logger.info("创建 document_segments 集合索引...")
            await mongodb.db["document_segments"].create_index("id", unique=True)
            await mongodb.db["document_segments"].create_index([
                ("document_id", 1),
                ("position", 1)
            ])
            await mongodb.db["document_segments"].create_index("dataset_id")
            await mongodb.db["document_segments"].create_index("hit_count")
            await mongodb.db["document_segments"].create_index("created_at")
            
            # 2. 创建子块集合的索引
            logger.info("创建 child_chunks 集合索引...")
            await mongodb.db["child_chunks"].create_index("id", unique=True)
            await mongodb.db["child_chunks"].create_index([
                ("segment_id", 1),
                ("position", 1)
            ])
            await mongodb.db["child_chunks"].create_index([
                ("index_node_id", 1),
                ("dataset_id", 1)
            ])
            await mongodb.db["child_chunks"].create_index("document_id")
            await mongodb.db["child_chunks"].create_index("dataset_id")
            await mongodb.db["child_chunks"].create_index("created_at")
            
            # 3. 确保现有documents集合的索引
            logger.info("确保 documents 集合索引...")
            await mongodb.db["documents"].create_index("id", unique=True)
            await mongodb.db["documents"].create_index("user_id")
            await mongodb.db["documents"].create_index("document_id")
            await mongodb.db["documents"].create_index("file_name")
            await mongodb.db["documents"].create_index("status")
            await mongodb.db["documents"].create_index("processing_method")
            await mongodb.db["documents"].create_index("created_at")
            
            logger.info("层次化存储集合和索引创建完成")
            
        except Exception as e:
            logger.error(f"创建集合和索引失败: {str(e)}")
            raise
    
    async def check_existing_data(self) -> Dict[str, int]:
        """检查现有数据"""
        try:
            logger.info("检查现有数据...")
            
            # 统计现有数据
            stats = {}
            
            # 检查documents集合
            stats["documents"] = await mongodb.db["documents"].count_documents({})
            stats["hierarchical_documents"] = await mongodb.db["documents"].count_documents({
                "processing_method": "hierarchical"
            })
            
            # 检查层次化集合
            stats["document_segments"] = await mongodb.db["document_segments"].count_documents({})
            stats["child_chunks"] = await mongodb.db["child_chunks"].count_documents({})
            
            logger.info(f"数据统计: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"检查现有数据失败: {str(e)}")
            raise
    
    async def migrate_existing_documents(self, dry_run: bool = True) -> Dict[str, Any]:
        """迁移现有文档（可选功能）
        
        Args:
            dry_run: 是否为试运行模式
            
        Returns:
            迁移结果统计
        """
        try:
            logger.info(f"开始迁移现有文档 (dry_run={dry_run})...")
            
            # 查找未使用层次化处理的文档
            query = {
                "$or": [
                    {"processing_method": {"$ne": "hierarchical"}},
                    {"processing_method": {"$exists": False}}
                ],
                "status": "ready"
            }
            
            cursor = mongodb.db["documents"].find(query)
            migration_stats = {
                "total_candidates": 0,
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "dry_run": dry_run
            }
            
            async for doc in cursor:
                migration_stats["total_candidates"] += 1
                
                try:
                    doc_id = doc.get("id")
                    file_name = doc.get("file_name", "unknown")
                    
                    logger.info(f"处理文档: {doc_id} - {file_name}")
                    
                    # 检查是否已经有层次化数据
                    existing_segments = await mongodb.db["document_segments"].count_documents({
                        "document_id": doc_id
                    })
                    
                    if existing_segments > 0:
                        logger.info(f"文档 {doc_id} 已有层次化数据，跳过")
                        migration_stats["skipped"] += 1
                        continue
                    
                    if not dry_run:
                        # 实际迁移逻辑
                        # 注意：这里需要根据具体需求实现迁移逻辑
                        # 由于迁移复杂，建议手动重新处理重要文档
                        
                        # 标记文档需要重新处理
                        await mongodb.db["documents"].update_one(
                            {"id": doc_id},
                            {"$set": {
                                "migration_status": "needs_reprocessing",
                                "migration_date": datetime.now(timezone.utc)
                            }}
                        )
                        
                        migration_stats["migrated"] += 1
                        logger.info(f"文档 {doc_id} 标记为需要重新处理")
                    else:
                        logger.info(f"[DRY RUN] 将标记文档 {doc_id} 需要重新处理")
                        migration_stats["migrated"] += 1
                
                except Exception as e:
                    logger.error(f"迁移文档失败: {str(e)}")
                    migration_stats["errors"] += 1
            
            logger.info(f"迁移完成: {migration_stats}")
            return migration_stats
            
        except Exception as e:
            logger.error(f"迁移现有文档失败: {str(e)}")
            raise
    
    async def validate_migration(self) -> Dict[str, Any]:
        """验证迁移结果"""
        try:
            logger.info("验证迁移结果...")
            
            validation_results = {
                "collections_exist": True,
                "indexes_exist": True,
                "data_integrity": True,
                "errors": []
            }
            
            # 1. 检查集合是否存在
            collections = await mongodb.db.list_collection_names()
            required_collections = ["documents", "document_segments", "child_chunks"]
            
            for collection in required_collections:
                if collection not in collections:
                    validation_results["collections_exist"] = False
                    validation_results["errors"].append(f"集合 {collection} 不存在")
            
            # 2. 检查索引
            for collection in required_collections:
                if collection in collections:
                    indexes = await mongodb.db[collection].list_indexes().to_list(None)
                    index_names = [idx["name"] for idx in indexes]
                    logger.info(f"集合 {collection} 的索引: {index_names}")
            
            # 3. 检查数据完整性
            # 检查父子关系完整性
            segments_count = await mongodb.db["document_segments"].count_documents({})
            chunks_count = await mongodb.db["child_chunks"].count_documents({})
            
            if segments_count > 0:
                # 检查孤立的子块
                pipeline = [
                    {
                        "$lookup": {
                            "from": "document_segments",
                            "localField": "segment_id",
                            "foreignField": "id",
                            "as": "parent"
                        }
                    },
                    {
                        "$match": {
                            "parent": {"$size": 0}
                        }
                    },
                    {
                        "$count": "orphaned_chunks"
                    }
                ]
                
                orphaned_result = await mongodb.db["child_chunks"].aggregate(pipeline).to_list(None)
                orphaned_count = orphaned_result[0]["orphaned_chunks"] if orphaned_result else 0
                
                if orphaned_count > 0:
                    validation_results["data_integrity"] = False
                    validation_results["errors"].append(f"发现 {orphaned_count} 个孤立的子块")
            
            validation_results["statistics"] = {
                "documents": await mongodb.db["documents"].count_documents({}),
                "document_segments": segments_count,
                "child_chunks": chunks_count,
                "hierarchical_documents": await mongodb.db["documents"].count_documents({
                    "processing_method": "hierarchical"
                })
            }
            
            logger.info(f"验证结果: {validation_results}")
            return validation_results
            
        except Exception as e:
            logger.error(f"验证迁移失败: {str(e)}")
            raise
    
    async def cleanup_old_data(self, confirm: bool = False):
        """清理旧数据（谨慎操作）"""
        if not confirm:
            logger.warning("清理旧数据需要确认，使用 --confirm-cleanup 参数")
            return
        
        try:
            logger.warning("开始清理旧数据...")
            
            # 这里可以添加清理逻辑，例如：
            # - 删除状态为 "failed" 的旧文档
            # - 清理过期的临时数据
            # - 整理碎片化的数据
            
            # 示例：清理失败的文档
            failed_docs = await mongodb.db["documents"].count_documents({"status": "failed"})
            logger.info(f"发现 {failed_docs} 个失败的文档")
            
            # 实际清理操作需要谨慎实施
            logger.info("清理操作需要手动确认每个步骤")
            
        except Exception as e:
            logger.error(f"清理数据失败: {str(e)}")
            raise


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="层次化RAG架构迁移工具")
    parser.add_argument("--create-collections", action="store_true", 
                       help="创建层次化存储的集合和索引")
    parser.add_argument("--check-data", action="store_true",
                       help="检查现有数据")
    parser.add_argument("--migrate", action="store_true",
                       help="迁移现有文档")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="试运行模式（默认启用）")
    parser.add_argument("--validate", action="store_true",
                       help="验证迁移结果")
    parser.add_argument("--cleanup", action="store_true",
                       help="清理旧数据")
    parser.add_argument("--confirm-cleanup", action="store_true",
                       help="确认清理操作")
    parser.add_argument("--all", action="store_true",
                       help="执行所有操作（除清理外）")
    
    args = parser.parse_args()
    
    if not any([args.create_collections, args.check_data, args.migrate, 
               args.validate, args.cleanup, args.all]):
        parser.print_help()
        return
    
    migrator = HierarchicalMigrator()
    
    try:
        # 连接数据库
        await migrator.connect_db()
        
        # 执行操作
        if args.all or args.create_collections:
            await migrator.create_hierarchical_collections()
        
        if args.all or args.check_data:
            await migrator.check_existing_data()
        
        if args.all or args.migrate:
            dry_run = args.dry_run if not args.all else True
            await migrator.migrate_existing_documents(dry_run=dry_run)
        
        if args.all or args.validate:
            await migrator.validate_migration()
        
        if args.cleanup:
            await migrator.cleanup_old_data(confirm=args.confirm_cleanup)
        
        logger.info("迁移操作完成")
        
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        sys.exit(1)
    
    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())