#!/usr/bin/env python3
"""
分析文档上传问题的详细脚本

基于之前的调查结果，重点分析为什么文档没有被保存到数据库中。
"""

import os
import sys
import json
import time
import requests
import asyncio
import motor.motor_asyncio
from datetime import datetime
from pathlib import Path
from pymilvus import connections, Collection, utility

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_FILE_PATH = "/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.txt"
MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB = "rag_chat"
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"

class UploadIssueAnalyzer:
    def __init__(self):
        self.test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0MkBleGFtcGxlLmNvbSIsImV4cCI6MTc1MTA2ODkzMX0.hK1ZSzjW12z6NXmipmmo-tvJqBel4W7U5jwoU_5DArI"
        
    def log_step(self, step_name, details=None):
        """记录分析步骤"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"\n{'='*80}")
        print(f"[{timestamp}] {step_name}")
        print(f"{'='*80}")
        if details:
            if isinstance(details, dict):
                print(json.dumps(details, indent=2, ensure_ascii=False))
            else:
                print(details)
    
    async def check_database_before_upload(self):
        """上传前检查数据库状态"""
        self.log_step("🔍 上传前检查数据库状态")
        
        # 检查MongoDB
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
            db = client[MONGODB_DB]
            collection = db['documents']
            
            # 获取最近的文档
            recent_docs = await collection.find().sort("created_at", -1).limit(5).to_list(length=5)
            print(f"MongoDB中最近的5个文档:")
            for i, doc in enumerate(recent_docs):
                if '_id' in doc:
                    del doc['_id']
                print(f"  {i+1}. ID: {doc.get('id')}, 文件名: {doc.get('file_name')}, 状态: {doc.get('status')}")
            
            await client.close()
            
        except Exception as e:
            print(f"❌ MongoDB检查失败: {e}")
        
        # 检查Milvus
        try:
            connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
            collection_name = "rag_documents"
            
            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                collection.load()
                
                # 获取总数量
                total_count = collection.num_entities
                print(f"Milvus中总向量数量: {total_count}")
                
                # 获取最近的一些向量
                if total_count > 0:
                    results = collection.query(
                        expr="id >= 0",
                        output_fields=["id", "doc_id", "content"],
                        limit=3
                    )
                    print(f"最近的3个向量:")
                    for i, result in enumerate(results):
                        print(f"  {i+1}. ID: {result.get('id')}, Doc ID: {result.get('doc_id')}")
            else:
                print(f"❌ Milvus集合 {collection_name} 不存在")
                
        except Exception as e:
            print(f"❌ Milvus检查失败: {e}")
    
    def test_upload_with_preview_mode(self):
        """测试预览模式上传"""
        self.log_step("🔍 测试预览模式上传")
        
        url = f"{API_BASE_URL}/rag/documents/upload"
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Accept': 'application/json'
        }
        
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')}
            data = {
                'parent_chunk_size': '1024',
                'parent_chunk_overlap': '200',
                'parent_separator': '\n\n',
                'child_chunk_size': '512',
                'child_chunk_overlap': '50',
                'child_separator': '\n',
                'preview_only': 'true'  # 预览模式
            }
            
            try:
                response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
                
                print(f"预览模式响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    print(f"预览模式响应:")
                    print(f"  - success: {response_data.get('success')}")
                    print(f"  - preview_mode: {response_data.get('preview_mode')}")
                    print(f"  - doc_id: {response_data.get('doc_id')}")
                    print(f"  - total_segments: {response_data.get('total_segments')}")
                    
                    return response_data
                else:
                    print(f"❌ 预览模式请求失败: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ 预览模式请求异常: {e}")
                return None
    
    def test_upload_with_full_mode(self):
        """测试完整模式上传"""
        self.log_step("🔍 测试完整模式上传")
        
        url = f"{API_BASE_URL}/rag/documents/upload"
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Accept': 'application/json'
        }
        
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')}
            data = {
                'parent_chunk_size': '1024',
                'parent_chunk_overlap': '200',
                'parent_separator': '\n\n',
                'child_chunk_size': '512',
                'child_chunk_overlap': '50',
                'child_separator': '\n',
                'preview_only': 'false'  # 完整模式
            }
            
            try:
                response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
                
                print(f"完整模式响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    print(f"完整模式响应:")
                    print(f"  - success: {response_data.get('success')}")
                    print(f"  - preview_mode: {response_data.get('preview_mode')}")
                    print(f"  - doc_id: {response_data.get('doc_id')}")
                    print(f"  - total_segments: {response_data.get('total_segments')}")
                    
                    return response_data
                else:
                    print(f"❌ 完整模式请求失败: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ 完整模式请求异常: {e}")
                return None
    
    async def check_database_after_upload(self, doc_id):
        """上传后检查数据库状态"""
        self.log_step(f"🔍 上传后检查数据库状态 (doc_id: {doc_id})")
        
        if not doc_id:
            print("❌ 没有doc_id，跳过检查")
            return
        
        # 等待一段时间让数据库操作完成
        print("⏳ 等待5秒让数据库操作完成...")
        await asyncio.sleep(5)
        
        # 检查MongoDB
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
            db = client[MONGODB_DB]
            collection = db['documents']
            
            # 查找特定文档
            doc = await collection.find_one({"id": doc_id})
            if doc:
                if '_id' in doc:
                    del doc['_id']
                print(f"✅ 在MongoDB中找到文档:")
                print(f"  - ID: {doc.get('id')}")
                print(f"  - 文件名: {doc.get('file_name')}")
                print(f"  - 状态: {doc.get('status')}")
                print(f"  - 段落数量: {doc.get('segments_count')}")
                print(f"  - 创建时间: {doc.get('created_at')}")
            else:
                print(f"❌ 在MongoDB中未找到文档 {doc_id}")
            
            await client.close()
            
        except Exception as e:
            print(f"❌ MongoDB检查失败: {e}")
        
        # 检查Milvus
        try:
            connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
            collection_name = "rag_documents"
            
            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                collection.load()
                
                # 查询特定文档的向量
                expr = f'doc_id == "{doc_id}"'
                results = collection.query(
                    expr=expr,
                    output_fields=["id", "doc_id", "content", "metadata"]
                )
                
                if results:
                    print(f"✅ 在Milvus中找到 {len(results)} 个向量:")
                    for i, result in enumerate(results[:3]):  # 只显示前3个
                        print(f"  {i+1}. ID: {result.get('id')}, 内容长度: {len(result.get('content', ''))}")
                else:
                    print(f"❌ 在Milvus中未找到文档 {doc_id} 的向量")
            else:
                print(f"❌ Milvus集合 {collection_name} 不存在")
                
        except Exception as e:
            print(f"❌ Milvus检查失败: {e}")
    
    def check_api_health(self):
        """检查API健康状态"""
        self.log_step("🔍 检查API健康状态")
        
        try:
            # 检查健康端点
            health_url = f"{API_BASE_URL.replace('/api/v1', '')}/health"
            response = requests.get(health_url, timeout=10)
            
            print(f"健康检查响应状态码: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"健康检查响应: {health_data}")
            else:
                print(f"健康检查失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
        
        # 检查用户认证
        try:
            user_url = f"{API_BASE_URL}/auth/me"
            headers = {'Authorization': f'Bearer {self.test_token}'}
            response = requests.get(user_url, headers=headers, timeout=10)
            
            print(f"用户认证响应状态码: {response.status_code}")
            if response.status_code == 200:
                user_data = response.json()
                print(f"当前用户: {user_data.get('email')}")
            else:
                print(f"用户认证失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 用户认证异常: {e}")
    
    async def run_analysis(self):
        """运行完整分析"""
        print("🔍 开始分析文档上传问题")
        print(f"测试文件: {TEST_FILE_PATH}")
        print(f"API地址: {API_BASE_URL}")
        
        # 1. 检查API健康状态
        self.check_api_health()
        
        # 2. 检查上传前的数据库状态
        await self.check_database_before_upload()
        
        # 3. 测试预览模式
        preview_result = self.test_upload_with_preview_mode()
        time.sleep(2)
        
        # 4. 测试完整模式
        full_result = self.test_upload_with_full_mode()
        
        # 5. 检查上传后的数据库状态
        if full_result and full_result.get('doc_id'):
            await self.check_database_after_upload(full_result['doc_id'])
        
        # 6. 总结分析结果
        self.log_step("📊 分析总结")
        
        print("🔍 关键发现:")
        
        if preview_result:
            print(f"✅ 预览模式工作正常: preview_mode={preview_result.get('preview_mode')}")
        else:
            print("❌ 预览模式失败")
        
        if full_result:
            print(f"✅ 完整模式API响应正常: preview_mode={full_result.get('preview_mode')}")
            print(f"   生成的doc_id: {full_result.get('doc_id')}")
        else:
            print("❌ 完整模式失败")
        
        print("\n🎯 下一步建议:")
        print("1. 检查后端日志中的详细错误信息")
        print("2. 验证数据库连接配置")
        print("3. 检查RAG服务的save_processed_document方法")
        print("4. 验证Milvus和MongoDB的连接状态")
        
        print("\n🎉 分析完成")

def main():
    """主函数"""
    analyzer = UploadIssueAnalyzer()
    asyncio.run(analyzer.run_analysis())

if __name__ == "__main__":
    main()
