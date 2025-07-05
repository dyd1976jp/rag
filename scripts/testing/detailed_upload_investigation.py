#!/usr/bin/env python3
"""
详细的文档上传调查脚本

此脚本用于深入调查页面文档上传功能与curl命令调用API时产生的结果不一致问题。
包括详细的日志记录、数据库内容检查、向量存储验证等。
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime
from pathlib import Path
import asyncio
import motor.motor_asyncio
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

class DetailedUploadInvestigator:
    def __init__(self):
        self.test_token = self._get_test_token()
        self.results = {}
        
    def _get_test_token(self):
        """获取测试token"""
        # 这里需要一个有效的token，可以从环境变量获取或手动设置
        token = os.getenv('TEST_TOKEN')
        if not token:
            # 使用一个示例token，实际使用时需要替换
            token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0MkBleGFtcGxlLmNvbSIsImV4cCI6MTc1MTA2ODkzMX0.hK1ZSzjW12z6NXmipmmo-tvJqBel4W7U5jwoU_5DArI"
        return token
    
    def log_step(self, step_name, details=None):
        """记录调查步骤"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"\n{'='*80}")
        print(f"[{timestamp}] {step_name}")
        print(f"{'='*80}")
        if details:
            if isinstance(details, dict):
                print(json.dumps(details, indent=2, ensure_ascii=False))
            else:
                print(details)
    
    def test_curl_upload(self):
        """测试curl命令上传"""
        self.log_step("🔍 测试curl命令上传")
        
        if not os.path.exists(TEST_FILE_PATH):
            print(f"❌ 测试文件不存在: {TEST_FILE_PATH}")
            return None
        
        # 构建curl命令 - 使用API默认参数
        curl_cmd = [
            'curl', '-X', 'POST',
            f'{API_BASE_URL}/rag/documents/upload',
            '-H', f'Authorization: Bearer {self.test_token}',
            '-H', 'Accept: application/json',
            '-F', f'file=@{TEST_FILE_PATH}',
            # 使用API默认参数（不显式设置，让API使用默认值）
            '-v'  # 详细输出
        ]
        
        print("执行curl命令（使用API默认参数）:")
        print(' '.join(curl_cmd))
        
        try:
            start_time = time.time()
            result = subprocess.run(
                curl_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            end_time = time.time()
            
            print(f"\n⏱️  执行时间: {end_time - start_time:.2f}秒")
            print(f"📊 返回码: {result.returncode}")
            
            # 解析响应
            response_data = None
            if result.stdout:
                try:
                    # 从curl的详细输出中提取JSON响应
                    lines = result.stdout.split('\n')
                    json_line = None
                    for line in lines:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            json_line = line
                            break
                    
                    if json_line:
                        response_data = json.loads(json_line)
                    else:
                        # 尝试解析整个输出
                        response_data = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON解析失败: {e}")
                    print(f"原始输出: {result.stdout}")
            
            curl_result = {
                'method': 'curl_default_params',
                'success': result.returncode == 0,
                'execution_time': end_time - start_time,
                'response': response_data,
                'raw_stdout': result.stdout,
                'raw_stderr': result.stderr,
                'return_code': result.returncode
            }
            
            self.results['curl_default'] = curl_result
            return curl_result
            
        except subprocess.TimeoutExpired:
            print("❌ curl命令执行超时")
            return None
        except Exception as e:
            print(f"❌ curl命令执行失败: {e}")
            return None
    
    def test_frontend_simulation(self):
        """测试模拟前端页面调用"""
        self.log_step("🔍 测试模拟前端页面调用")
        
        if not os.path.exists(TEST_FILE_PATH):
            print(f"❌ 测试文件不存在: {TEST_FILE_PATH}")
            return None
        
        # 模拟前端页面的参数设置
        url = f"{API_BASE_URL}/rag/documents/upload"
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Accept': 'application/json'
            # 注意：不设置Content-Type，让requests自动处理
        }
        
        # 前端页面使用的参数（基于代码分析）
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')}
            data = {
                'parent_chunk_size': '1024',
                'parent_chunk_overlap': '200',
                'parent_separator': '\n\n',  # 前端使用真实换行符
                'child_chunk_size': '512',   # Math.floor(1024 / 2)
                'child_chunk_overlap': '50', # Math.floor(200 / 4)
                'child_separator': '\n',     # 前端使用真实换行符
                'preview_only': 'false'      # 明确设置为false
            }
            
            print("模拟前端请求参数:")
            print(f"URL: {url}")
            print(f"Headers: {headers}")
            print(f"Data: {data}")
            
            try:
                start_time = time.time()
                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=120
                )
                end_time = time.time()
                
                print(f"\n⏱️  执行时间: {end_time - start_time:.2f}秒")
                print(f"📊 响应状态码: {response.status_code}")
                print(f"📋 响应头: {dict(response.headers)}")
                
                response_data = None
                try:
                    response_data = response.json()
                    print(f"📄 响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                except json.JSONDecodeError:
                    print(f"⚠️  响应不是JSON格式: {response.text}")
                
                frontend_result = {
                    'method': 'frontend_simulation',
                    'success': response.status_code == 200,
                    'execution_time': end_time - start_time,
                    'status_code': response.status_code,
                    'response': response_data,
                    'raw_response': response.text,
                    'headers': dict(response.headers)
                }
                
                self.results['frontend_simulation'] = frontend_result
                return frontend_result
                
            except requests.RequestException as e:
                print(f"❌ 前端模拟请求失败: {e}")
                return None
    
    async def check_mongodb_content(self, doc_ids):
        """检查MongoDB中的文档内容"""
        self.log_step("🔍 检查MongoDB中的文档内容")
        
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
            db = client[MONGODB_DB]
            collection = db['documents']
            
            mongodb_results = {}
            
            for method, doc_id in doc_ids.items():
                if not doc_id:
                    continue
                    
                print(f"\n检查 {method} 的文档 {doc_id}:")
                
                # 查找文档
                doc = await collection.find_one({"id": doc_id})
                if doc:
                    # 移除_id字段以便JSON序列化
                    if '_id' in doc:
                        del doc['_id']
                    
                    mongodb_results[method] = {
                        'found': True,
                        'document': doc
                    }
                    
                    print(f"✅ 找到文档:")
                    print(f"  - 文件名: {doc.get('file_name')}")
                    print(f"  - 状态: {doc.get('status')}")
                    print(f"  - 段落数量: {doc.get('segments_count')}")
                    print(f"  - 创建时间: {doc.get('created_at')}")
                    print(f"  - 更新时间: {doc.get('updated_at')}")
                else:
                    mongodb_results[method] = {
                        'found': False,
                        'document': None
                    }
                    print(f"❌ 未找到文档")
            
            await client.close()
            self.results['mongodb_check'] = mongodb_results
            return mongodb_results
            
        except Exception as e:
            print(f"❌ MongoDB检查失败: {e}")
            return None
    
    def check_milvus_content(self, doc_ids):
        """检查Milvus中的向量内容"""
        self.log_step("🔍 检查Milvus中的向量内容")
        
        try:
            # 连接到Milvus
            connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
            
            # 检查集合
            collection_name = "rag_documents"
            if not utility.has_collection(collection_name):
                print(f"❌ 集合 {collection_name} 不存在")
                return None
            
            collection = Collection(collection_name)
            collection.load()
            
            milvus_results = {}
            
            for method, doc_id in doc_ids.items():
                if not doc_id:
                    continue
                    
                print(f"\n检查 {method} 的向量数据 {doc_id}:")
                
                # 查询向量数据
                expr = f'doc_id == "{doc_id}"'
                results = collection.query(
                    expr=expr,
                    output_fields=["id", "doc_id", "content", "metadata"]
                )
                
                milvus_results[method] = {
                    'vector_count': len(results),
                    'vectors': results[:3] if results else []  # 只保存前3个用于对比
                }
                
                print(f"✅ 找到 {len(results)} 个向量")
                if results:
                    print(f"  - 第一个向量ID: {results[0].get('id')}")
                    print(f"  - 内容长度: {len(results[0].get('content', ''))}")
            
            self.results['milvus_check'] = milvus_results
            return milvus_results
            
        except Exception as e:
            print(f"❌ Milvus检查失败: {e}")
            return None
    
    def compare_results(self):
        """对比分析结果"""
        self.log_step("📊 对比分析结果")
        
        curl_result = self.results.get('curl_default')
        frontend_result = self.results.get('frontend_simulation')
        
        if not curl_result or not frontend_result:
            print("❌ 无法进行对比，某个测试失败")
            return
        
        print("🔍 API响应对比:")
        
        # 对比基本信息
        curl_success = curl_result.get('success', False)
        frontend_success = frontend_result.get('success', False)
        
        print(f"curl成功: {curl_success}")
        print(f"frontend成功: {frontend_success}")
        print(f"执行时间对比: curl={curl_result.get('execution_time', 0):.2f}s, frontend={frontend_result.get('execution_time', 0):.2f}s")
        
        # 对比响应数据
        curl_response = curl_result.get('response')
        frontend_response = frontend_result.get('response')
        
        if curl_response and frontend_response:
            print("\n📋 响应数据对比:")
            
            key_fields = ['success', 'message', 'doc_id', 'segments_count', 'total_segments']
            differences = []
            
            for field in key_fields:
                curl_value = curl_response.get(field)
                frontend_value = frontend_response.get(field)
                
                if curl_value == frontend_value:
                    print(f"✅ {field}: {curl_value} (一致)")
                else:
                    print(f"❌ {field}: curl={curl_value}, frontend={frontend_value} (不一致)")
                    differences.append(field)
            
            if differences:
                print(f"\n⚠️  发现 {len(differences)} 个不一致字段: {differences}")
            else:
                print(f"\n✅ 所有关键字段都一致")
        
        # 对比数据库内容
        mongodb_check = self.results.get('mongodb_check', {})
        milvus_check = self.results.get('milvus_check', {})
        
        if mongodb_check:
            print(f"\n🗄️  MongoDB内容对比:")
            for method in ['curl_default', 'frontend_simulation']:
                mongo_data = mongodb_check.get(method, {})
                if mongo_data.get('found'):
                    doc = mongo_data.get('document', {})
                    print(f"{method}: segments_count={doc.get('segments_count')}, status={doc.get('status')}")
                else:
                    print(f"{method}: 未找到文档")
        
        if milvus_check:
            print(f"\n🔍 Milvus向量对比:")
            for method in ['curl_default', 'frontend_simulation']:
                milvus_data = milvus_check.get(method, {})
                vector_count = milvus_data.get('vector_count', 0)
                print(f"{method}: 向量数量={vector_count}")
    
    def save_results(self):
        """保存调查结果"""
        output_file = project_root / 'temp' / 'detailed_upload_investigation_results.json'
        output_file.parent.mkdir(exist_ok=True)
        
        results_with_timestamp = {
            'timestamp': datetime.now().isoformat(),
            'test_file': TEST_FILE_PATH,
            'results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_with_timestamp, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 详细调查结果已保存到: {output_file}")
    
    async def run_investigation(self):
        """运行完整调查"""
        print("🔍 开始详细的文档上传调查")
        print(f"测试文件: {TEST_FILE_PATH}")
        print(f"API地址: {API_BASE_URL}")
        
        # 检查测试文件
        if not os.path.exists(TEST_FILE_PATH):
            print(f"❌ 测试文件不存在: {TEST_FILE_PATH}")
            return
        
        # 执行测试
        curl_result = self.test_curl_upload()
        time.sleep(3)  # 等待3秒避免冲突
        
        frontend_result = self.test_frontend_simulation()
        time.sleep(2)  # 等待2秒
        
        # 提取文档ID用于数据库检查
        doc_ids = {}
        if curl_result and curl_result.get('response'):
            doc_ids['curl_default'] = curl_result['response'].get('doc_id')
        if frontend_result and frontend_result.get('response'):
            doc_ids['frontend_simulation'] = frontend_result['response'].get('doc_id')
        
        # 检查数据库内容
        if doc_ids:
            await self.check_mongodb_content(doc_ids)
            self.check_milvus_content(doc_ids)
        
        # 对比分析
        self.compare_results()
        
        # 保存结果
        self.save_results()
        
        print("\n🎉 详细调查完成")

def main():
    """主函数"""
    investigator = DetailedUploadInvestigator()
    asyncio.run(investigator.run_investigation())

if __name__ == "__main__":
    main()
