import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.db.mongodb import mongodb
from app.models.document_collection import DocumentCollection, DocumentCollectionCreate, DocumentCollectionUpdate

logger = logging.getLogger(__name__)

class DocumentCollectionService:
    def __init__(self):
        self.collection_name = "document_collections"
        self.documents_collection_name = "documents"

    async def create_collection(self, user_id: str, data: DocumentCollectionCreate) -> Optional[DocumentCollection]:
        """创建文档集"""
        try:
            # 输入验证
            if not user_id:
                logger.error("创建文档集失败: user_id不能为空")
                return None
                
            if not data.name or not data.name.strip():
                logger.error("创建文档集失败: 文档集名称不能为空")
                return None

            # 检查同名文档集
            existing = await mongodb.db[self.collection_name].find_one({
                "user_id": user_id,
                "name": data.name
            })
            if existing:
                logger.warning(f"用户 {user_id} 已存在同名文档集: {data.name}")
                return None

            collection_data = {
                "id": str(uuid.uuid4()),
                "name": data.name.strip(),
                "description": data.description.strip() if data.description else "",
                "user_id": user_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "document_count": 0,
                "tags": [tag.strip() for tag in (data.tags or []) if tag.strip()]
            }
            
            logger.info(f"正在创建文档集: user_id={user_id}, name={collection_data['name']}")
            result = await mongodb.db[self.collection_name].insert_one(collection_data)
            
            if result.inserted_id:
                collection_data["_id"] = str(result.inserted_id)
                logger.info(f"文档集创建成功: id={collection_data['id']}")
                return DocumentCollection(**collection_data)
            
            logger.error("文档集创建失败: MongoDB插入失败")
            return None
            
        except Exception as e:
            logger.error(f"创建文档集失败: {str(e)}", exc_info=True)
            return None

    async def get_user_collections(self, user_id: str) -> List[DocumentCollection]:
        """获取用户的所有文档集"""
        try:
            cursor = mongodb.db[self.collection_name].find({"user_id": user_id})
            collections = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                collections.append(DocumentCollection(**doc))
            return collections
        except Exception as e:
            logger.error(f"获取用户文档集失败: {str(e)}")
            return []

    async def get_collection_by_id(self, collection_id: str, user_id: str) -> Optional[DocumentCollection]:
        """获取文档集详情"""
        try:
            doc = await mongodb.db[self.collection_name].find_one({
                "id": collection_id,
                "user_id": user_id
            })
            if doc:
                doc["_id"] = str(doc["_id"])
                return DocumentCollection(**doc)
            return None
        except Exception as e:
            logger.error(f"获取文档集详情失败: {str(e)}")
            return None

    async def update_collection(
        self, 
        collection_id: str, 
        user_id: str, 
        data: DocumentCollectionUpdate
    ) -> Optional[DocumentCollection]:
        """更新文档集"""
        try:
            update_data = {
                "updated_at": datetime.now()
            }
            if data.name is not None:
                update_data["name"] = data.name
            if data.description is not None:
                update_data["description"] = data.description
            if data.tags is not None:
                update_data["tags"] = data.tags

            result = await mongodb.db[self.collection_name].update_one(
                {"id": collection_id, "user_id": user_id},
                {"$set": update_data}
            )
            
            if result.modified_count:
                return await self.get_collection_by_id(collection_id, user_id)
            return None
        except Exception as e:
            logger.error(f"更新文档集失败: {str(e)}")
            return None

    async def delete_collection(self, collection_id: str, user_id: str) -> bool:
        """删除文档集"""
        try:
            # 首先删除文档集中的所有文档
            await mongodb.db[self.documents_collection_name].update_many(
                {"collection_id": collection_id},
                {"$set": {"collection_id": None}}
            )
            
            # 然后删除文档集
            result = await mongodb.db[self.collection_name].delete_one({
                "id": collection_id,
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"删除文档集失败: {str(e)}")
            return False

    async def add_document_to_collection(
        self, 
        collection_id: str, 
        document_id: str, 
        user_id: str
    ) -> bool:
        """将文档添加到文档集"""
        try:
            # 验证文档集存在且属于该用户
            collection = await self.get_collection_by_id(collection_id, user_id)
            if not collection:
                return False

            # 更新文档的collection_id
            result = await mongodb.db[self.documents_collection_name].update_one(
                {"id": document_id, "user_id": user_id},
                {"$set": {"collection_id": collection_id}}
            )

            if result.modified_count:
                # 更新文档集的文档计数
                await mongodb.db[self.collection_name].update_one(
                    {"id": collection_id},
                    {"$inc": {"document_count": 1}}
                )
                return True
            return False
        except Exception as e:
            logger.error(f"添加文档到文档集失败: {str(e)}")
            return False

    async def remove_document_from_collection(
        self, 
        collection_id: str, 
        document_id: str, 
        user_id: str
    ) -> bool:
        """从文档集中移除文档"""
        try:
            # 验证文档集存在且属于该用户
            collection = await self.get_collection_by_id(collection_id, user_id)
            if not collection:
                return False

            # 更新文档的collection_id为None
            result = await mongodb.db[self.documents_collection_name].update_one(
                {
                    "id": document_id,
                    "user_id": user_id,
                    "collection_id": collection_id
                },
                {"$set": {"collection_id": None}}
            )

            if result.modified_count:
                # 更新文档集的文档计数
                await mongodb.db[self.collection_name].update_one(
                    {"id": collection_id},
                    {"$inc": {"document_count": -1}}
                )
                return True
            return False
        except Exception as e:
            logger.error(f"从文档集中移除文档失败: {str(e)}")
            return False

    async def get_collection_documents(
        self, 
        collection_id: str, 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """获取文档集中的所有文档"""
        try:
            cursor = mongodb.db[self.documents_collection_name].find({
                "collection_id": collection_id,
                "user_id": user_id
            })
            documents = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                documents.append(doc)
            return documents
        except Exception as e:
            logger.error(f"获取文档集文档失败: {str(e)}")
            return []

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档"""
        try:
            doc = await mongodb.db[self.documents_collection_name].find_one({"id": document_id})
            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
            return None
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None