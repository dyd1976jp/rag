#!/usr/bin/env python3
"""
文档切割功能一致性验证脚本

验证前端页面预览显示的文档切割结果与实际保存到数据库中的切割结果是否完全一致。

测试内容：
1. 前端预览模式：POST /api/v1/rag/documents/upload (preview_only=true)
2. 数据库保存模式：POST /api/v1/rag/documents/upload (preview_only=false)
3. 对比两种模式的切割结果一致性
4. 生成详细的测试报告

测试文件：data/uploads/初赛训练数据集.txt

作者: RAG项目团队
日期: 2025-06-29
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx
import logging
from dataclasses import dataclass, asdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_chunking_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ChunkData:
    """切割块数据结构"""
    id: int
    content: str
    start: int
    end: int
    length: int
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ChunkingResult:
    """切割结果数据结构"""
    success: bool
    message: str
    total_segments: int
    segments: List[ChunkData]
    parent_content: str
    children_content: List[str]
    source: str  # 'preview' 或 'database'
    timestamp: float
    parameters: Dict[str, Any]

class DocumentChunkingVerifier:
    """文档切割功能一致性验证器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_file_path = "data/uploads/初赛训练数据集.txt"
        self.auth_token = None
        self.test_results = {}
        
    async def setup_authentication(self) -> bool:
        """设置认证"""
        try:
            async with httpx.AsyncClient() as client:
                # 登录获取token
                login_data = {
                    "username": "admin",
                    "password": "admin123"
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    data=login_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.auth_token = result.get("access_token")
                    logger.info("✅ 认证成功")
                    return True
                else:
                    logger.error(f"❌ 认证失败: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 认证过程出错: {str(e)}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        if not self.auth_token:
            raise ValueError("未设置认证token")
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def test_preview_api_chunking(self, chunk_params: Dict[str, Any]) -> ChunkingResult:
        """测试前端预览API的文档切割（使用文件上传预览模式）"""
        logger.info("🔍 开始测试前端预览API的文档切割...")

        try:
            # 准备文件上传（预览模式）
            with open(self.test_file_path, 'rb') as f:
                files = {"file": (os.path.basename(self.test_file_path), f, "text/plain")}

                # 准备表单数据（预览模式）
                data = {
                    "parent_chunk_size": str(chunk_params["parent_chunk_size"]),
                    "parent_chunk_overlap": str(chunk_params["parent_chunk_overlap"]),
                    "parent_separator": chunk_params["parent_separator"],
                    "child_chunk_size": str(chunk_params["child_chunk_size"]),
                    "child_chunk_overlap": str(chunk_params["child_chunk_overlap"]),
                    "child_separator": chunk_params["child_separator"],
                    "preview_only": "true"  # 关键：设置为预览模式
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/api/v1/rag/documents/upload",
                        files=files,
                        data=data,
                        headers=self.get_auth_headers()
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 转换为标准格式
                    segments = []
                    if result.get("segments"):
                        for seg in result["segments"]:
                            segments.append(ChunkData(
                                id=seg["id"],
                                content=seg["content"],
                                start=seg.get("start", 0),
                                end=seg.get("end", len(seg["content"])),
                                length=seg.get("length", len(seg["content"])),
                                metadata=seg.get("metadata", {})
                            ))
                    
                    chunking_result = ChunkingResult(
                        success=result.get("success", False),
                        message=result.get("message", ""),
                        total_segments=result.get("total_segments", 0),
                        segments=segments,
                        parent_content=result.get("parentContent", ""),
                        children_content=result.get("childrenContent", []),
                        source="preview",
                        timestamp=time.time(),
                        parameters=chunk_params
                    )
                    
                    logger.info(f"✅ 前端预览API测试成功，生成 {len(segments)} 个切割块")
                    return chunking_result
                    
                else:
                    logger.error(f"❌ 前端预览API请求失败: {response.status_code} - {response.text}")
                    return ChunkingResult(
                        success=False,
                        message=f"API请求失败: {response.status_code}",
                        total_segments=0,
                        segments=[],
                        parent_content="",
                        children_content=[],
                        source="preview",
                        timestamp=time.time(),
                        parameters=chunk_params
                    )
                    
        except Exception as e:
            logger.error(f"❌ 前端预览API测试出错: {str(e)}")
            return ChunkingResult(
                success=False,
                message=f"测试出错: {str(e)}",
                total_segments=0,
                segments=[],
                parent_content="",
                children_content=[],
                source="preview",
                timestamp=time.time(),
                parameters=chunk_params
            )
    
    async def test_database_save_chunking(self, chunk_params: Dict[str, Any]) -> ChunkingResult:
        """测试数据库保存API的文档切割（实际保存模式）"""
        logger.info("🔍 开始测试数据库保存API的文档切割...")

        try:
            # 准备文件上传（实际保存模式）
            with open(self.test_file_path, 'rb') as f:
                files = {"file": (os.path.basename(self.test_file_path), f, "text/plain")}

                # 准备表单数据（不设置preview_only，实际保存到数据库）
                data = {
                    "parent_chunk_size": str(chunk_params["parent_chunk_size"]),
                    "parent_chunk_overlap": str(chunk_params["parent_chunk_overlap"]),
                    "parent_separator": chunk_params["parent_separator"],
                    "child_chunk_size": str(chunk_params["child_chunk_size"]),
                    "child_chunk_overlap": str(chunk_params["child_chunk_overlap"]),
                    "child_separator": chunk_params["child_separator"]
                    # 注意：不设置preview_only，这样会实际保存到数据库
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/api/v1/rag/documents/upload",
                        files=files,
                        data=data,
                        headers=self.get_auth_headers()
                    )
                    
                    if response.status_code == 200:
                        result = response.json()

                        # 数据库保存模式的响应格式不同，需要特殊处理
                        segments = []
                        total_segments = 0
                        parent_content = ""
                        children_content = []

                        # 检查是否是保存模式的简单响应
                        if "segments_count" in result and "segments" not in result:
                            # 这是保存模式的响应，只有统计信息，没有详细内容
                            total_segments = result.get("segments_count", 0)
                            logger.warning(f"⚠️ 数据库保存模式只返回统计信息，无详细切割内容")
                        else:
                            # 这是预览模式的响应，有详细内容
                            if result.get("segments"):
                                for seg in result["segments"]:
                                    segments.append(ChunkData(
                                        id=seg["id"],
                                        content=seg["content"],
                                        start=seg.get("start", 0),
                                        end=seg.get("end", len(seg["content"])),
                                        length=seg.get("length", len(seg["content"])),
                                        metadata=seg.get("metadata", {})
                                    ))
                            total_segments = result.get("total_segments", len(segments))
                            parent_content = result.get("parentContent", "")
                            children_content = result.get("childrenContent", [])

                        chunking_result = ChunkingResult(
                            success=result.get("success", False),
                            message=result.get("message", ""),
                            total_segments=total_segments,
                            segments=segments,
                            parent_content=parent_content,
                            children_content=children_content,
                            source="database",
                            timestamp=time.time(),
                            parameters=chunk_params
                        )

                        logger.info(f"✅ 数据库保存API测试成功，统计显示 {total_segments} 个切割块，详细内容 {len(segments)} 个")
                        return chunking_result
                        
                    else:
                        logger.error(f"❌ 数据库保存API请求失败: {response.status_code} - {response.text}")
                        return ChunkingResult(
                            success=False,
                            message=f"API请求失败: {response.status_code}",
                            total_segments=0,
                            segments=[],
                            parent_content="",
                            children_content=[],
                            source="database",
                            timestamp=time.time(),
                            parameters=chunk_params
                        )
                        
        except Exception as e:
            logger.error(f"❌ 数据库保存API测试出错: {str(e)}")
            return ChunkingResult(
                success=False,
                message=f"测试出错: {str(e)}",
                total_segments=0,
                segments=[],
                parent_content="",
                children_content=[],
                source="database",
                timestamp=time.time(),
                parameters=chunk_params
            )

    def compare_chunking_results(self, preview_result: ChunkingResult, database_result: ChunkingResult) -> Dict[str, Any]:
        """对比两个切割结果的一致性"""
        logger.info("🔍 开始对比切割结果一致性...")

        comparison = {
            "timestamp": time.time(),
            "test_file": self.test_file_path,
            "parameters": preview_result.parameters,
            "preview_result": {
                "success": preview_result.success,
                "total_segments": preview_result.total_segments,
                "parent_content_length": len(preview_result.parent_content),
                "children_count": len(preview_result.children_content)
            },
            "database_result": {
                "success": database_result.success,
                "total_segments": database_result.total_segments,
                "parent_content_length": len(database_result.parent_content),
                "children_count": len(database_result.children_content)
            },
            "consistency_check": {},
            "detailed_differences": [],
            "summary": {}
        }

        # 1. 检查基本一致性
        consistency = comparison["consistency_check"]

        # 成功状态一致性
        consistency["success_status"] = preview_result.success == database_result.success

        # 切割块数量一致性
        consistency["segment_count"] = preview_result.total_segments == database_result.total_segments

        # 父内容一致性
        consistency["parent_content"] = preview_result.parent_content == database_result.parent_content

        # 子内容数量一致性
        consistency["children_count"] = len(preview_result.children_content) == len(database_result.children_content)

        # 2. 详细对比每个切割块
        differences = []
        min_segments = min(len(preview_result.segments), len(database_result.segments))

        for i in range(min_segments):
            preview_seg = preview_result.segments[i]
            database_seg = database_result.segments[i]

            content_match = preview_seg.content == database_seg.content
            length_match = preview_seg.length == database_seg.length
            start_match = preview_seg.start == database_seg.start
            end_match = preview_seg.end == database_seg.end

            seg_diff = {
                "segment_id": i,
                "content_match": content_match,
                "length_match": length_match,
                "start_match": start_match,
                "end_match": end_match
            }

            # 只有当存在真正的差异时才记录
            if not all([content_match, length_match, start_match, end_match]):
                seg_diff["preview_content_length"] = len(preview_seg.content)
                seg_diff["database_content_length"] = len(database_seg.content)
                seg_diff["preview_start"] = preview_seg.start
                seg_diff["database_start"] = database_seg.start
                seg_diff["preview_end"] = preview_seg.end
                seg_diff["database_end"] = database_seg.end
                differences.append(seg_diff)

        comparison["detailed_differences"] = differences

        # 3. 对比子内容
        children_differences = []
        min_children = min(len(preview_result.children_content), len(database_result.children_content))

        for i in range(min_children):
            if preview_result.children_content[i] != database_result.children_content[i]:
                children_differences.append({
                    "child_index": i,
                    "preview_length": len(preview_result.children_content[i]),
                    "database_length": len(database_result.children_content[i]),
                    "content_match": False
                })

        comparison["children_differences"] = children_differences

        # 4. 生成总结
        total_checks = len(consistency)
        passed_checks = sum(1 for v in consistency.values() if v)

        comparison["summary"] = {
            "overall_consistency": passed_checks == total_checks and len(differences) == 0 and len(children_differences) == 0,
            "consistency_score": passed_checks / total_checks if total_checks > 0 else 0,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "segment_differences_count": len(differences),
            "children_differences_count": len(children_differences)
        }

        logger.info(f"✅ 一致性对比完成，一致性得分: {comparison['summary']['consistency_score']:.2%}")

        return comparison

    def generate_detailed_report(self, comparison: Dict[str, Any]) -> str:
        """生成详细的测试报告"""
        logger.info("📝 生成详细测试报告...")

        report_lines = [
            "# 文档切割功能一致性验证报告",
            f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(comparison['timestamp']))}",
            f"**测试文件**: {comparison['test_file']}",
            "",
            "## 测试参数",
            f"- 父块大小: {comparison['parameters']['parent_chunk_size']}",
            f"- 父块重叠: {comparison['parameters']['parent_chunk_overlap']}",
            f"- 父块分隔符: '{comparison['parameters']['parent_separator']}'",
            f"- 子块大小: {comparison['parameters']['child_chunk_size']}",
            f"- 子块重叠: {comparison['parameters']['child_chunk_overlap']}",
            f"- 子块分隔符: '{comparison['parameters']['child_separator']}'",
            "",
            "## 测试结果概览",
            f"- **整体一致性**: {'✅ 通过' if comparison['summary']['overall_consistency'] else '❌ 不通过'}",
            f"- **一致性得分**: {comparison['summary']['consistency_score']:.2%}",
            f"- **通过检查项**: {comparison['summary']['passed_checks']}/{comparison['summary']['total_checks']}",
            "",
            "## 前端预览API结果",
            f"- 成功状态: {comparison['preview_result']['success']}",
            f"- 切割块数量: {comparison['preview_result']['total_segments']}",
            f"- 父内容长度: {comparison['preview_result']['parent_content_length']} 字符",
            f"- 子内容数量: {comparison['preview_result']['children_count']}",
            "",
            "## 数据库保存API结果",
            f"- 成功状态: {comparison['database_result']['success']}",
            f"- 切割块数量: {comparison['database_result']['total_segments']}",
            f"- 父内容长度: {comparison['database_result']['parent_content_length']} 字符",
            f"- 子内容数量: {comparison['database_result']['children_count']}",
            "",
            "## 一致性检查详情"
        ]

        # 添加一致性检查结果
        for check_name, result in comparison["consistency_check"].items():
            status = "✅ 一致" if result else "❌ 不一致"
            report_lines.append(f"- {check_name}: {status}")

        # 添加差异详情
        if comparison["detailed_differences"]:
            report_lines.extend([
                "",
                "## 切割块差异详情",
                f"发现 {len(comparison['detailed_differences'])} 个切割块存在差异："
            ])

            for diff in comparison["detailed_differences"]:
                report_lines.extend([
                    f"",
                    f"### 切割块 {diff['segment_id']}",
                    f"- 内容匹配: {'✅' if diff['content_match'] else '❌'}",
                    f"- 长度匹配: {'✅' if diff['length_match'] else '❌'}",
                    f"- 起始位置匹配: {'✅' if diff['start_match'] else '❌'}",
                    f"- 结束位置匹配: {'✅' if diff['end_match'] else '❌'}"
                ])

                if not diff['content_match']:
                    report_lines.extend([
                        f"- 前端预览长度: {diff.get('preview_content_length', 'N/A')}",
                        f"- 数据库保存长度: {diff.get('database_content_length', 'N/A')}"
                    ])

        # 添加子内容差异
        if comparison.get("children_differences"):
            report_lines.extend([
                "",
                "## 子内容差异详情",
                f"发现 {len(comparison['children_differences'])} 个子内容存在差异："
            ])

            for diff in comparison["children_differences"]:
                report_lines.extend([
                    f"- 子内容 {diff['child_index']}: 长度不匹配 (前端: {diff['preview_length']}, 数据库: {diff['database_length']})"
                ])

        # 添加结论和建议
        report_lines.extend([
            "",
            "## 结论和建议"
        ])

        if comparison["summary"]["overall_consistency"]:
            report_lines.append("✅ **结论**: 前端预览和数据库保存的文档切割功能完全一致，功能正常。")
        else:
            # 检查是否是API响应格式差异导致的不一致
            preview_has_details = comparison["preview_result"]["total_segments"] > 0 and comparison["preview_result"]["parent_content_length"] > 0
            database_has_details = comparison["database_result"]["parent_content_length"] > 0

            if preview_has_details and not database_has_details:
                report_lines.extend([
                    "❌ **结论**: 发现API响应格式不一致的问题。",
                    "",
                    "**主要问题**:",
                    "- 前端预览模式 (preview_only=true) 返回详细的切割内容",
                    "- 数据库保存模式 (preview_only=false) 只返回统计信息，不返回详细内容",
                    "- 这导致用户在前端看到的预览结果与实际保存的数据格式不一致",
                    "",
                    "**建议修复措施**:",
                    "1. **统一API响应格式**: 保存模式也应该返回详细的切割结果",
                    "2. **添加可选参数**: 允许保存模式选择是否返回详细内容",
                    "3. **文档说明**: 在API文档中明确说明两种模式的响应差异",
                    "4. **前端适配**: 前端代码应该处理两种不同的响应格式"
                ])
            else:
                report_lines.extend([
                    "❌ **结论**: 发现前端预览和数据库保存的文档切割结果存在不一致。",
                    "",
                    "**建议修复措施**:",
                    "1. 检查两个API是否使用了相同的切割参数和算法",
                    "2. 验证文档预处理步骤是否一致",
                    "3. 确认切割器配置和规则是否相同",
                    "4. 检查响应格式化逻辑是否存在差异"
                ])

        return "\n".join(report_lines)

    async def run_verification(self) -> Dict[str, Any]:
        """运行完整的验证流程"""
        logger.info("🚀 开始文档切割功能一致性验证...")

        # 检查测试文件是否存在
        if not os.path.exists(self.test_file_path):
            logger.error(f"❌ 测试文件不存在: {self.test_file_path}")
            return {"error": "测试文件不存在"}

        # 设置认证
        if not await self.setup_authentication():
            return {"error": "认证失败"}

        # 定义测试参数
        chunk_params = {
            "parent_chunk_size": 512,
            "parent_chunk_overlap": 50,
            "parent_separator": "\n\n",
            "child_chunk_size": 256,
            "child_chunk_overlap": 25,
            "child_separator": "\n"
        }

        # 测试前端预览API
        preview_result = await self.test_preview_api_chunking(chunk_params)

        # 测试数据库保存API
        database_result = await self.test_database_save_chunking(chunk_params)

        # 对比结果
        comparison = self.compare_chunking_results(preview_result, database_result)

        # 生成报告
        report = self.generate_detailed_report(comparison)

        # 保存结果
        results = {
            "preview_result": asdict(preview_result),
            "database_result": asdict(database_result),
            "comparison": comparison,
            "report": report
        }

        # 保存到文件
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = f"document_chunking_verification_results_{timestamp}.json"
        report_file = f"document_chunking_verification_report_{timestamp}.md"

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✅ 验证完成，结果已保存到: {results_file}")
        logger.info(f"✅ 报告已保存到: {report_file}")

        return results

async def main():
    """主函数"""
    verifier = DocumentChunkingVerifier()
    results = await verifier.run_verification()

    if "error" in results:
        logger.error(f"❌ 验证失败: {results['error']}")
        return

    # 打印简要结果
    comparison = results["comparison"]
    summary = comparison["summary"]

    print("\n" + "="*60)
    print("📊 文档切割功能一致性验证结果")
    print("="*60)
    print(f"整体一致性: {'✅ 通过' if summary['overall_consistency'] else '❌ 不通过'}")
    print(f"一致性得分: {summary['consistency_score']:.2%}")
    print(f"通过检查项: {summary['passed_checks']}/{summary['total_checks']}")
    print(f"切割块差异: {summary['segment_differences_count']} 个")
    print(f"子内容差异: {summary['children_differences_count']} 个")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
