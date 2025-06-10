"""
MongoDB模拟模块，用于在没有真实MongoDB连接时进行测试
"""
import asyncio
from datetime import datetime
import uuid
from typing import Dict, List, Any, Optional
from bson import ObjectId

class MockCollection:
    """模拟MongoDB集合"""
    
    def __init__(self, name):
        self.name = name
        self.documents = []
        
    async def insert_one(self, document):
        """插入单个文档"""
        if "_id" not in document:
            document["_id"] = ObjectId()
        self.documents.append(document)
        return MockInsertResult(document["_id"])
    
    async def find_one(self, filter_dict):
        """查找单个文档"""
        for doc in self.documents:
            match = True
            for key, value in filter_dict.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                return doc
        return None
    
    async def update_one(self, filter_dict, update_dict):
        """更新单个文档"""
        modified_count = 0
        for i, doc in enumerate(self.documents):
            match = True
            for key, value in filter_dict.items():
                if key == "_id" and isinstance(value, ObjectId):
                    if str(doc["_id"]) != str(value):
                        match = False
                        break
                elif key not in doc or doc[key] != value:
                    match = False
                    break
            
            if match:
                # 处理$set操作符
                if "$set" in update_dict:
                    for key, value in update_dict["$set"].items():
                        self.documents[i][key] = value
                # 直接更新
                else:
                    for key, value in update_dict.items():
                        self.documents[i][key] = value
                        
                modified_count += 1
                break
                
        return MockUpdateResult(modified_count)
    
    async def delete_one(self, filter_dict):
        """删除单个文档"""
        deleted_count = 0
        for i, doc in enumerate(self.documents):
            match = True
            for key, value in filter_dict.items():
                if key == "_id" and isinstance(value, ObjectId):
                    if str(doc["_id"]) != str(value):
                        match = False
                        break
                elif key not in doc or doc[key] != value:
                    match = False
                    break
            
            if match:
                self.documents.pop(i)
                deleted_count = 1
                break
                
        return MockDeleteResult(deleted_count)
    
    async def delete_many(self, filter_dict):
        """删除多个文档"""
        original_count = len(self.documents)
        
        # 如果有正则表达式模式，特殊处理
        if any(isinstance(v, dict) and "$regex" in v for v in filter_dict.values()):
            to_delete = []
            for i, doc in enumerate(self.documents):
                match = True
                for key, value in filter_dict.items():
                    if isinstance(value, dict) and "$regex" in value:
                        pattern = value["$regex"]
                        if key not in doc or not str(doc[key]).startswith(pattern[1:]):  # 去掉^前缀
                            match = False
                            break
                    elif key not in doc or doc[key] != value:
                        match = False
                        break
                
                if match:
                    to_delete.append(i)
                    
            # 从后往前删除，避免索引问题
            for i in sorted(to_delete, reverse=True):
                self.documents.pop(i)
        else:
            # 常规匹配删除
            self.documents = [doc for doc in self.documents if not all(
                key in doc and doc[key] == value for key, value in filter_dict.items()
            )]
        
        deleted_count = original_count - len(self.documents)
        return MockDeleteResult(deleted_count)
    
    def find(self):
        """返回所有文档的游标"""
        return MockCursor(self.documents)
    
    async def update_many(self, filter_dict, update_dict):
        """更新多个文档"""
        modified_count = 0
        for i, doc in enumerate(self.documents):
            match = True
            for key, value in filter_dict.items():
                if key == "_id" and isinstance(value, dict) and "$ne" in value:
                    # 处理 {"_id": {"$ne": some_id}} 的情况
                    ne_value = value["$ne"]
                    if str(doc["_id"]) == str(ne_value):
                        match = False
                        break
                elif key not in doc or doc[key] != value:
                    match = False
                    break
            
            if match:
                # 处理$set操作符
                if "$set" in update_dict:
                    for key, value in update_dict["$set"].items():
                        self.documents[i][key] = value
                # 直接更新
                else:
                    for key, value in update_dict.items():
                        self.documents[i][key] = value
                        
                modified_count += 1
                
        return MockUpdateResult(modified_count)
        
    async def command(self, command_name, *args, **kwargs):
        """执行命令"""
        if command_name == "buildinfo":
            return {"version": "5.0.0-mock", "gitVersion": "mock-version"}
        return {}
    
    async def list_collection_names(self):
        """列出集合名称"""
        return [self.name]


class MockCursor:
    """模拟MongoDB游标"""
    
    def __init__(self, documents):
        self.documents = documents.copy()
        self.current_index = 0
        self._skip_val = 0
        self._limit_val = None
        
    def skip(self, skip):
        """跳过指定数量的文档"""
        self._skip_val = skip
        return self
        
    def limit(self, limit):
        """限制返回文档的数量"""
        self._limit_val = limit
        return self
    
    def _get_filtered_docs(self):
        """获取应用了skip和limit的文档列表"""
        if self._limit_val:
            return self.documents[self._skip_val:self._skip_val + self._limit_val]
        return self.documents[self._skip_val:]
    
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        """异步迭代器方法"""
        filtered_docs = self._get_filtered_docs()
        if self.current_index >= len(filtered_docs):
            raise StopAsyncIteration
            
        doc = filtered_docs[self.current_index]
        self.current_index += 1
        return doc


class MockInsertResult:
    """模拟插入结果"""
    
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        
        
class MockUpdateResult:
    """模拟更新结果"""
    
    def __init__(self, modified_count):
        self.modified_count = modified_count
        
        
class MockDeleteResult:
    """模拟删除结果"""
    
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class MockDatabase:
    """模拟MongoDB数据库"""
    
    def __init__(self, name):
        self.name = name
        self.collections = {}
        
    def __getitem__(self, collection_name):
        """获取集合"""
        if collection_name not in self.collections:
            self.collections[collection_name] = MockCollection(collection_name)
        return self.collections[collection_name]
    
    def __getattr__(self, collection_name):
        """通过属性方式获取集合"""
        return self[collection_name]
        
    def get_collection(self, collection_name):
        """获取集合"""
        return self[collection_name]
        
    async def list_collection_names(self):
        """列出集合名称"""
        return list(self.collections.keys())
        
    async def command(self, command, *args, **kwargs):
        """执行命令"""
        if command == "buildinfo":
            return {"version": "5.0.0-mock", "gitVersion": "mock-version"}
        return {}


class MockMongoDB:
    """模拟MongoDB客户端"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        
    async def connect_to_database(self):
        """连接到数据库"""
        self.db = MockDatabase("mock_db")
        self.connected = True
        return self.db
        
    async def close_database_connection(self):
        """关闭数据库连接"""
        self.connected = False
        
    def get_collection(self, collection_name):
        """获取集合"""
        if not self.db:
            raise Exception("Database not connected")
        return self.db[collection_name]


# 全局模拟MongoDB实例
mongodb = MockMongoDB() 