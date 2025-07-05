#!/usr/bin/env python3
"""
诊断文档存储问题

此脚本用于诊断为什么API返回成功但文档没有存储到数据库的问题。
"""

import json
import requests
import time
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "backend"))

from backend.app.db.mongodb import mongodb
from pymilvus import connections, Collection

class StorageIssueDiagnoser:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0MkBleGFtcGxlLmNvbSIsImV4cCI6MTc1MTA2ODkzMX0.hK1ZSzjW12z6NXmipmmo-tvJqBel4W7U5jwoU_5DArI"
        self.test_file = "/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.txt"
        self.mongodb_collection = "documents"
        self.milvus_collection = "rag_documents"
        
    async def connect_databases(self):
        """连接数据库"""
        try:
            await mongodb.connect()
            connections.connect(host='localhost', port='19530')
            print("✅ 数据库连接成功")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {str(e)}")
            return False
    
    def test_upload_with_monitoring(self) -> Dict[str, Any]:
        """测试上传并监控存储过程"""
        print("\n=== 测试文档上传并监控存储过程 ===")
        
        # 使用简单参数进行测试
        params = {
            'preview_only': 'false'
        }
        
        try:
            files = {'file': open(self.test_file, 'rb')}
            headers = {'Authorization': f'Bearer {self.token}'}
            
            print("发送上传请求...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/v1/rag/documents/upload",
                headers=headers,
                files=files,
                data=params
            )
            
            files['file'].close()
            request_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ API请求成功 (耗时: {request_time:.2f}秒)")
                print(f"  文档ID: {response_data.get('doc_id')}")
                print(f"  响应消息: {response_data.get('message')}")
                print(f"  预览模式: {response_data.get('preview_mode')}")
                
                return {
                    'success': True,
                    'doc_id': response_data.get('doc_id'),
                    'response': response_data,
                    'request_time': request_time
                }
            else:
                print(f"❌ API请求失败: {response.status_code}")
                print(f"  错误信息: {response.text}")
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def monitor_storage_process(self, doc_id: str, max_wait_time: int = 30):
        """监控存储过程"""
        print(f"\n=== 监控文档存储过程 (文档ID: {doc_id}) ===")
        
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次
        
        while time.time() - start_time < max_wait_time:
            elapsed = time.time() - start_time
            print(f"\n检查时间点: {elapsed:.1f}秒")
            
            # 检查MongoDB
            try:
                mongo_doc = await mongodb.db[self.mongodb_collection].find_one({"id": doc_id})
                if mongo_doc:
                    print(f"✅ MongoDB: 文档已存储")
                    print(f"  状态: {mongo_doc.get('status')}")
                    print(f"  段落数: {mongo_doc.get('segments_count')}")
                    print(f"  创建时间: {mongo_doc.get('created_at')}")
                else:
                    print(f"❌ MongoDB: 文档未找到")
            except Exception as e:
                print(f"❌ MongoDB检查失败: {str(e)}")
            
            # 检查Milvus
            try:
                collection = Collection(self.milvus_collection)
                expr = f'doc_id == "{doc_id}"'
                vectors = collection.query(
                    expr=expr,
                    output_fields=["id", "doc_id"],
                    limit=1
                )
                
                if vectors:
                    print(f"✅ Milvus: 找到向量数据")
                    
                    # 获取总数
                    all_vectors = collection.query(
                        expr=expr,
                        output_fields=["id"],
                        limit=1000
                    )
                    print(f"  向量总数: {len(all_vectors)}")
                else:
                    print(f"❌ Milvus: 未找到向量数据")
            except Exception as e:
                print(f"❌ Milvus检查失败: {str(e)}")
            
            # 等待下次检查
            if time.time() - start_time < max_wait_time:
                await asyncio.sleep(check_interval)
        
        print(f"\n监控结束 (总耗时: {time.time() - start_time:.1f}秒)")
    
    async def check_service_health(self):
        """检查服务健康状态"""
        print("\n=== 检查服务健康状态 ===")
        
        # 检查API服务
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                print("✅ API服务正常运行")
            else:
                print(f"❌ API服务异常: {response.status_code}")
        except Exception as e:
            print(f"❌ API服务连接失败: {str(e)}")
        
        # 检查数据库连接
        try:
            # MongoDB
            await mongodb.connect()
            collections = await mongodb.db.list_collection_names()
            print(f"✅ MongoDB连接正常，集合数: {len(collections)}")
            
            # Milvus
            connections.connect(host='localhost', port='19530')
            from pymilvus import utility
            collections = utility.list_collections()
            print(f"✅ Milvus连接正常，集合数: {len(collections)}")
            
        except Exception as e:
            print(f"❌ 数据库连接检查失败: {str(e)}")
    
    async def check_existing_documents(self):
        """检查现有文档"""
        print("\n=== 检查现有文档 ===")
        
        try:
            # 检查MongoDB中的文档
            cursor = mongodb.db[self.mongodb_collection].find().sort("created_at", -1).limit(5)
            documents = await cursor.to_list(length=5)
            
            print(f"MongoDB中最近的5个文档:")
            for i, doc in enumerate(documents, 1):
                print(f"  {i}. ID: {doc.get('id', 'N/A')[:8]}...")
                print(f"     文件名: {doc.get('file_name', 'N/A')}")
                print(f"     状态: {doc.get('status', 'N/A')}")
                print(f"     段落数: {doc.get('segments_count', 'N/A')}")
                print(f"     创建时间: {doc.get('created_at', 'N/A')}")
                
                # 检查对应的Milvus数据
                doc_id = doc.get('id')
                if doc_id:
                    try:
                        collection = Collection(self.milvus_collection)
                        expr = f'doc_id == "{doc_id}"'
                        vectors = collection.query(expr=expr, output_fields=["id"], limit=1000)
                        print(f"     Milvus向量数: {len(vectors)}")
                    except Exception as e:
                        print(f"     Milvus检查失败: {str(e)}")
                print()
                
        except Exception as e:
            print(f"❌ 检查现有文档失败: {str(e)}")
    
    async def run_diagnosis(self):
        """运行完整诊断"""
        print("开始文档存储问题诊断")
        print("=" * 60)
        
        # 检查服务健康状态
        await self.check_service_health()
        
        # 检查现有文档
        await self.check_existing_documents()
        
        # 连接数据库
        if not await self.connect_databases():
            return
        
        # 测试上传
        upload_result = self.test_upload_with_monitoring()
        
        if upload_result['success']:
            doc_id = upload_result['doc_id']
            
            # 监控存储过程
            await self.monitor_storage_process(doc_id, max_wait_time=30)
            
            # 最终检查
            print("\n=== 最终存储状态检查 ===")
            try:
                mongo_doc = await mongodb.db[self.mongodb_collection].find_one({"id": doc_id})
                if mongo_doc:
                    print(f"✅ 最终MongoDB状态: 文档已存储")
                    print(f"  状态: {mongo_doc.get('status')}")
                else:
                    print(f"❌ 最终MongoDB状态: 文档未存储")
                
                collection = Collection(self.milvus_collection)
                expr = f'doc_id == "{doc_id}"'
                vectors = collection.query(expr=expr, output_fields=["id"], limit=1000)
                
                if vectors:
                    print(f"✅ 最终Milvus状态: 向量已存储 ({len(vectors)}个)")
                else:
                    print(f"❌ 最终Milvus状态: 向量未存储")
                    
            except Exception as e:
                print(f"❌ 最终检查失败: {str(e)}")
        
        print("\n=== 诊断总结 ===")
        if upload_result['success']:
            print("1. ✅ API请求成功，返回正确响应")
            print("2. ❓ 需要检查存储过程是否完成")
            print("3. 💡 建议检查后端日志以了解存储失败原因")
        else:
            print("1. ❌ API请求失败")
            print("2. 💡 建议检查后端服务状态和配置")

async def main():
    """主函数"""
    diagnoser = StorageIssueDiagnoser()
    await diagnoser.run_diagnosis()

if __name__ == "__main__":
    asyncio.run(main())
