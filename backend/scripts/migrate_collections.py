#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Milvus集合迁移脚本

将现有集合迁移到支持动态字段的新schema。
"""

import os
import sys
import logging
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.collection_manager import collection_manager
from pymilvus import connections, Collection, utility
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_existing_collections() -> List[str]:
    """列出所有现有集合"""
    try:
        if not collection_manager.connect():
            logger.error("无法连接到Milvus服务器")
            return []
        
        collections = collection_manager.list_collections()
        logger.info(f"发现 {len(collections)} 个集合: {collections}")
        return collections
    
    except Exception as e:
        logger.error(f"列出集合失败: {e}")
        return []


def analyze_collection(collection_name: str) -> Dict[str, Any]:
    """分析集合的当前状态"""
    try:
        info = collection_manager.get_collection_info(collection_name)
        
        if not info.get("exists", False):
            return {"exists": False}
        
        logger.info(f"\n=== 集合分析: {collection_name} ===")
        logger.info(f"描述: {info.get('description', 'N/A')}")
        logger.info(f"动态字段支持: {info.get('enable_dynamic_field', False)}")
        logger.info(f"实体数量: {info.get('num_entities', 0)}")
        
        logger.info("字段列表:")
        for field in info.get("fields", []):
            logger.info(f"  - {field['name']}: {field['type']} (主键: {field.get('is_primary', False)})")
            if field.get('dimension'):
                logger.info(f"    维度: {field['dimension']}")
            if field.get('max_length'):
                logger.info(f"    最大长度: {field['max_length']}")
        
        logger.info("索引列表:")
        for index in info.get("indexes", []):
            logger.info(f"  - {index['field_name']}: {index.get('params', {})}")
        
        return info
    
    except Exception as e:
        logger.error(f"分析集合 {collection_name} 失败: {e}")
        return {"exists": False, "error": str(e)}


def backup_collection_data(collection_name: str) -> bool:
    """备份集合数据（可选实现）"""
    try:
        collection = Collection(collection_name)
        num_entities = collection.num_entities
        
        if num_entities == 0:
            logger.info(f"集合 {collection_name} 为空，无需备份")
            return True
        
        logger.warning(f"集合 {collection_name} 包含 {num_entities} 条数据")
        logger.warning("注意: 当前版本不支持自动数据迁移，请手动备份重要数据")
        
        # TODO: 实现数据备份逻辑
        # 这里可以添加将数据导出到文件的逻辑
        
        return True
    
    except Exception as e:
        logger.error(f"备份集合 {collection_name} 失败: {e}")
        return False


def migrate_collection(collection_name: str, force: bool = False) -> bool:
    """迁移单个集合"""
    try:
        logger.info(f"\n🔄 开始迁移集合: {collection_name}")
        
        # 分析当前集合
        info = analyze_collection(collection_name)
        
        if not info.get("exists", False):
            logger.warning(f"集合 {collection_name} 不存在，跳过")
            return False
        
        # 检查是否已经支持动态字段
        if info.get("enable_dynamic_field", False):
            logger.info(f"✅ 集合 {collection_name} 已支持动态字段，无需迁移")
            return True
        
        # 检查是否有数据
        num_entities = info.get("num_entities", 0)
        if num_entities > 0 and not force:
            logger.warning(f"⚠️  集合 {collection_name} 包含 {num_entities} 条数据")
            logger.warning("数据迁移需要手动处理，使用 --force 参数强制迁移（将丢失数据）")
            return False
        
        # 备份数据（如果需要）
        if num_entities > 0:
            logger.info("正在备份数据...")
            if not backup_collection_data(collection_name):
                logger.error("数据备份失败，中止迁移")
                return False
        
        # 创建新的集合名称
        new_collection_name = f"{collection_name}_migrated"
        backup_collection_name = f"{collection_name}_backup"
        
        # 获取向量维度（从现有字段中推断）
        dimension = 768  # 默认维度
        for field in info.get("fields", []):
            if field.get("dimension"):
                dimension = field["dimension"]
                break
        
        logger.info(f"使用向量维度: {dimension}")
        
        # 创建新集合
        logger.info(f"创建新集合: {new_collection_name}")
        new_collection = collection_manager.create_collection(
            collection_name=new_collection_name,
            dimension=dimension,
            drop_existing=True
        )
        
        if not new_collection:
            logger.error("创建新集合失败")
            return False
        
        # 创建索引
        logger.info("创建索引...")
        if not collection_manager.create_indexes(new_collection):
            logger.error("创建索引失败")
            return False
        
        # 重命名集合（Milvus不直接支持重命名，需要手动处理）
        logger.info("重命名集合...")
        
        # 1. 将原集合重命名为备份
        if utility.has_collection(collection_name):
            # 由于Milvus不支持直接重命名，我们需要提示用户手动处理
            logger.warning(f"请手动处理以下步骤:")
            logger.warning(f"1. 如果需要保留原数据，请备份集合 {collection_name}")
            logger.warning(f"2. 删除原集合: utility.drop_collection('{collection_name}')")
            logger.warning(f"3. 将新集合 {new_collection_name} 重命名为 {collection_name}")
            
            if force:
                logger.info(f"强制模式：删除原集合 {collection_name}")
                utility.drop_collection(collection_name)
                
                # 由于Milvus不支持重命名，我们创建一个同名的新集合
                final_collection = collection_manager.create_collection(
                    collection_name=collection_name,
                    dimension=dimension,
                    drop_existing=True
                )
                
                if final_collection:
                    collection_manager.create_indexes(final_collection)
                    logger.info(f"✅ 集合 {collection_name} 迁移完成")
                    
                    # 清理临时集合
                    if utility.has_collection(new_collection_name):
                        utility.drop_collection(new_collection_name)
                    
                    return True
        
        logger.info(f"✅ 新集合 {new_collection_name} 创建完成（支持动态字段）")
        return True
    
    except Exception as e:
        logger.error(f"迁移集合 {collection_name} 失败: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Milvus集合迁移工具")
    parser.add_argument("--collection", "-c", help="指定要迁移的集合名称")
    parser.add_argument("--all", "-a", action="store_true", help="迁移所有集合")
    parser.add_argument("--force", "-f", action="store_true", help="强制迁移（将丢失现有数据）")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析集合，不执行迁移")
    
    args = parser.parse_args()
    
    logger.info("🚀 Milvus集合迁移工具启动")
    
    # 连接到Milvus
    if not collection_manager.connect():
        logger.error("❌ 无法连接到Milvus服务器")
        return 1
    
    try:
        # 获取集合列表
        if args.collection:
            collections_to_process = [args.collection]
        elif args.all:
            collections_to_process = list_existing_collections()
        else:
            collections_to_process = list_existing_collections()
            if not collections_to_process:
                logger.info("没有发现任何集合")
                return 0
            
            print("\n发现以下集合:")
            for i, name in enumerate(collections_to_process, 1):
                print(f"{i}. {name}")
            
            choice = input("\n请选择要迁移的集合编号（或输入 'all' 迁移所有集合）: ").strip()
            
            if choice.lower() == 'all':
                pass  # 处理所有集合
            elif choice.isdigit() and 1 <= int(choice) <= len(collections_to_process):
                collections_to_process = [collections_to_process[int(choice) - 1]]
            else:
                logger.error("无效选择")
                return 1
        
        # 处理集合
        success_count = 0
        total_count = len(collections_to_process)
        
        for collection_name in collections_to_process:
            if args.analyze_only:
                analyze_collection(collection_name)
            else:
                if migrate_collection(collection_name, args.force):
                    success_count += 1
        
        if not args.analyze_only:
            logger.info(f"\n📊 迁移完成: {success_count}/{total_count} 个集合迁移成功")
        
        return 0 if success_count == total_count else 1
    
    except KeyboardInterrupt:
        logger.info("\n⏹️  用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"❌ 迁移过程中出现错误: {e}")
        return 1
    finally:
        collection_manager.disconnect()


if __name__ == "__main__":
    exit(main())
