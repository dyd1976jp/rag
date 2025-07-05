#!/usr/bin/env python3
"""
检查数据库中存储的文档内容

此脚本用于检查MongoDB和Milvus中实际存储的文档内容，
对比不同上传方式产生的数据差异。
"""

import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "backend"))

from backend.app.db.mongodb import mongodb
from backend.app.core.config import settings
from pymilvus import connections, Collection

class DatabaseContentChecker:
    def __init__(self):
        self.mongodb_collection = "documents"
        self.milvus_collection = "rag_documents"
        
    async def connect_databases(self):
        """连接数据库"""
        try:
            # 连接MongoDB
            await mongodb.connect()
            print("✅ MongoDB连接成功")
            
            # 连接Milvus
            connections.connect(host='localhost', port='19530')
            print("✅ Milvus连接成功")
            
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {str(e)}")
            return False
    
    async def get_recent_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近上传的文档"""
        try:
            cursor = mongodb.db[self.mongodb_collection].find().sort("created_at", -1).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            print(f"✅ 找到 {len(documents)} 个最近的文档")
            return documents
        except Exception as e:
            print(f"❌ 获取文档失败: {str(e)}")
            return []
    
    async def get_document_vectors(self, doc_id: str) -> List[Dict[str, Any]]:
        """获取文档的向量数据"""
        try:
            collection = Collection(self.milvus_collection)
            
            # 查询该文档的所有向量
            expr = f'doc_id == "{doc_id}"'
            results = collection.query(
                expr=expr,
                output_fields=["id", "doc_id", "content", "metadata"]
            )
            
            print(f"✅ 文档 {doc_id} 有 {len(results)} 个向量段落")
            return results
        except Exception as e:
            print(f"❌ 获取向量数据失败: {str(e)}")
            return []
    
    async def analyze_document_content(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个文档的内容"""
        doc_id = doc_info.get("id")
        file_name = doc_info.get("file_name")
        
        print(f"\n=== 分析文档: {file_name} (ID: {doc_id}) ===")
        
        # 获取向量数据
        vectors = await self.get_document_vectors(doc_id)
        
        analysis = {
            "doc_id": doc_id,
            "file_name": file_name,
            "created_at": doc_info.get("created_at"),
            "status": doc_info.get("status"),
            "segments_count": doc_info.get("segments_count"),
            "vector_count": len(vectors),
            "content_analysis": {}
        }
        
        if vectors:
            # 分析内容
            contents = [v.get("content", "") for v in vectors]
            total_chars = sum(len(c) for c in contents)
            avg_length = total_chars / len(contents) if contents else 0
            
            analysis["content_analysis"] = {
                "total_segments": len(contents),
                "total_characters": total_chars,
                "average_segment_length": round(avg_length, 2),
                "first_segment": contents[0] if contents else "",
                "last_segment": contents[-1] if contents else "",
                "segment_lengths": [len(c) for c in contents[:5]]  # 前5个段落的长度
            }
            
            print(f"  总段落数: {len(contents)}")
            print(f"  总字符数: {total_chars}")
            print(f"  平均段落长度: {avg_length:.2f}")
            print(f"  第一个段落: {contents[0][:50]}..." if contents else "  无内容")
        
        return analysis
    
    async def compare_documents(self, analyses: List[Dict[str, Any]]):
        """对比多个文档的差异"""
        print("\n" + "=" * 60)
        print("文档内容对比分析")
        print("=" * 60)
        
        if len(analyses) < 2:
            print("需要至少2个文档才能进行对比")
            return
        
        # 按时间排序
        analyses.sort(key=lambda x: x.get("created_at", datetime.min))
        
        base_analysis = analyses[0]
        print(f"\n基准文档: {base_analysis['file_name']} (ID: {base_analysis['doc_id'][:8]}...)")
        
        for i, analysis in enumerate(analyses[1:], 1):
            print(f"\n{i}. 对比文档: {analysis['file_name']} (ID: {analysis['doc_id'][:8]}...)")
            
            # 对比关键指标
            base_content = base_analysis.get("content_analysis", {})
            current_content = analysis.get("content_analysis", {})
            
            metrics = [
                ("总段落数", "total_segments"),
                ("总字符数", "total_characters"),
                ("平均段落长度", "average_segment_length")
            ]
            
            for metric_name, metric_key in metrics:
                base_val = base_content.get(metric_key, 0)
                current_val = current_content.get(metric_key, 0)
                
                if base_val == current_val:
                    print(f"  ✅ {metric_name}: {current_val} (相同)")
                else:
                    print(f"  ❌ {metric_name}: {current_val} vs {base_val} (不同)")
            
            # 对比第一个段落内容
            base_first = base_content.get("first_segment", "")
            current_first = current_content.get("first_segment", "")
            
            if base_first == current_first:
                print(f"  ✅ 第一个段落内容: 相同")
            else:
                print(f"  ❌ 第一个段落内容: 不同")
                print(f"    基准: {base_first[:50]}...")
                print(f"    当前: {current_first[:50]}...")
    
    async def run_analysis(self):
        """运行完整分析"""
        print("开始数据库内容检查")
        print("=" * 60)
        
        # 连接数据库
        if not await self.connect_databases():
            return
        
        # 获取最近的文档
        documents = await self.get_recent_documents(limit=10)
        
        if not documents:
            print("没有找到任何文档")
            return
        
        # 分析每个文档
        analyses = []
        for doc in documents:
            analysis = await self.analyze_document_content(doc)
            analyses.append(analysis)
        
        # 对比文档
        await self.compare_documents(analyses)
        
        # 保存分析结果
        output_file = "database_content_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n详细分析结果已保存到: {output_file}")
        
        # 关闭数据库连接
        await mongodb.disconnect()
        connections.disconnect("default")

async def main():
    """主函数"""
    checker = DatabaseContentChecker()
    await checker.run_analysis()

if __name__ == "__main__":
    asyncio.run(main())
