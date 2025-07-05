#!/usr/bin/env python3
"""
文档组织和整理脚本

分析和整理项目文档，包括：
- 识别重复或相似的文档
- 合并相关的修复文档
- 更新过时的文档内容
- 统一文档格式
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json
from datetime import datetime
from collections import defaultdict


class DocumentationOrganizer:
    """文档组织器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.docs_dir = self.project_root / "docs"
        self.analysis_results = {
            "duplicate_docs": [],
            "outdated_docs": [],
            "merge_candidates": [],
            "format_issues": [],
            "recommendations": []
        }
        
    def analyze_fix_documents(self) -> Dict:
        """分析修复文档"""
        print("🔍 分析修复文档...")
        
        fixes_dir = self.docs_dir / "fixes"
        if not fixes_dir.exists():
            return {}
        
        # 按主题分组修复文档
        topic_groups = defaultdict(list)
        
        for doc_file in fixes_dir.glob("*.md"):
            filename = doc_file.name.upper()
            
            # 识别主题
            if "DOCUMENT_PREVIEW" in filename:
                topic_groups["document_preview"].append(doc_file)
            elif "FRONTEND" in filename:
                topic_groups["frontend"].append(doc_file)
            elif "API" in filename:
                topic_groups["api"].append(doc_file)
            elif "MILVUS" in filename:
                topic_groups["milvus"].append(doc_file)
            elif "UTF8" in filename or "ENCODING" in filename:
                topic_groups["encoding"].append(doc_file)
            else:
                topic_groups["other"].append(doc_file)
        
        # 分析每个主题组
        for topic, docs in topic_groups.items():
            if len(docs) > 3:  # 如果同一主题有超过3个文档
                self.analysis_results["merge_candidates"].append({
                    "topic": topic,
                    "documents": [str(doc.relative_to(self.project_root)) for doc in docs],
                    "count": len(docs),
                    "suggestion": f"考虑将{topic}相关的{len(docs)}个文档合并为一个综合文档"
                })
        
        return topic_groups
    
    def check_document_freshness(self) -> None:
        """检查文档的时效性"""
        print("🔍 检查文档时效性...")
        
        cutoff_date = datetime.now().timestamp() - (30 * 24 * 3600)  # 30天前
        
        for doc_file in self.docs_dir.rglob("*.md"):
            try:
                mtime = doc_file.stat().st_mtime
                
                if mtime < cutoff_date:
                    # 检查是否为修复文档（修复文档通常是历史记录，不需要更新）
                    if "fixes" not in str(doc_file):
                        self.analysis_results["outdated_docs"].append({
                            "file": str(doc_file.relative_to(self.project_root)),
                            "last_modified": datetime.fromtimestamp(mtime).isoformat(),
                            "days_old": int((datetime.now().timestamp() - mtime) / (24 * 3600))
                        })
                        
            except Exception as e:
                print(f"   警告: 无法检查文件 {doc_file}: {e}")
    
    def analyze_document_structure(self) -> None:
        """分析文档结构和格式"""
        print("🔍 分析文档结构...")
        
        for doc_file in self.docs_dir.rglob("*.md"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                issues = []
                
                # 检查是否有标题
                if not content.startswith('#'):
                    issues.append("缺少主标题")
                
                # 检查是否有过长的行
                lines = content.split('\n')
                long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 120]
                if long_lines:
                    issues.append(f"存在过长行: {long_lines[:5]}")  # 只显示前5个
                
                # 检查是否有TODO或FIXME
                if re.search(r'\b(TODO|FIXME|XXX)\b', content, re.IGNORECASE):
                    issues.append("包含待办事项标记")
                
                if issues:
                    self.analysis_results["format_issues"].append({
                        "file": str(doc_file.relative_to(self.project_root)),
                        "issues": issues
                    })
                    
            except Exception as e:
                print(f"   警告: 无法分析文件 {doc_file}: {e}")
    
    def find_duplicate_content(self) -> None:
        """查找重复内容"""
        print("🔍 查找重复内容...")
        
        # 简单的重复检测：比较文件大小和前几行内容
        doc_signatures = {}
        
        for doc_file in self.docs_dir.rglob("*.md"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 创建文档签名（文件大小 + 前100个字符的hash）
                size = len(content)
                preview = content[:100].strip()
                signature = (size, hash(preview))
                
                if signature in doc_signatures:
                    self.analysis_results["duplicate_docs"].append({
                        "files": [
                            str(doc_signatures[signature].relative_to(self.project_root)),
                            str(doc_file.relative_to(self.project_root))
                        ],
                        "signature": f"size:{size}, preview_hash:{hash(preview)}"
                    })
                else:
                    doc_signatures[signature] = doc_file
                    
            except Exception as e:
                print(f"   警告: 无法检查文件 {doc_file}: {e}")
    
    def generate_recommendations(self) -> None:
        """生成整理建议"""
        print("🔍 生成整理建议...")
        
        recommendations = []
        
        # 基于分析结果生成建议
        if self.analysis_results["merge_candidates"]:
            recommendations.append({
                "type": "merge",
                "priority": "high",
                "description": "合并相关主题的修复文档",
                "details": self.analysis_results["merge_candidates"]
            })
        
        if self.analysis_results["outdated_docs"]:
            recommendations.append({
                "type": "update",
                "priority": "medium", 
                "description": "更新过时的文档",
                "details": f"发现{len(self.analysis_results['outdated_docs'])}个超过30天未更新的文档"
            })
        
        if self.analysis_results["duplicate_docs"]:
            recommendations.append({
                "type": "deduplicate",
                "priority": "medium",
                "description": "处理重复文档",
                "details": f"发现{len(self.analysis_results['duplicate_docs'])}组可能重复的文档"
            })
        
        if self.analysis_results["format_issues"]:
            recommendations.append({
                "type": "format",
                "priority": "low",
                "description": "修复格式问题",
                "details": f"发现{len(self.analysis_results['format_issues'])}个文档存在格式问题"
            })
        
        # 添加具体的整理建议
        recommendations.extend([
            {
                "type": "structure",
                "priority": "high",
                "description": "创建文档索引",
                "action": "在docs/README.md中创建完整的文档索引和导航"
            },
            {
                "type": "archive",
                "priority": "medium", 
                "description": "归档历史修复文档",
                "action": "将docs/fixes/中的旧修复文档移动到docs/fixes/archive/目录"
            },
            {
                "type": "standardize",
                "priority": "medium",
                "description": "标准化文档格式",
                "action": "为所有文档添加统一的头部信息（标题、日期、作者、状态）"
            }
        ])
        
        self.analysis_results["recommendations"] = recommendations
    
    def create_documentation_index(self) -> None:
        """创建文档索引"""
        print("📝 创建文档索引...")
        
        index_content = """# 项目文档索引

## 📚 文档导航

### 🏗️ 架构和设计
- [项目架构](ARCHITECTURE.md) - 系统架构设计文档
- [代码质量标准](CODE_QUALITY.md) - 代码质量和规范
- [依赖管理](DEPENDENCIES.md) - 项目依赖说明

### 🔧 API文档
- [API参考](API_REFERENCE.md) - 完整的API接口文档
- [API详细文档](api/API_DOCUMENTATION.md) - 详细的API使用说明
- [端点统一](api/ENDPOINT_UNIFICATION.md) - API端点规范

### 🚀 部署和运维
- [启动指南](deployment/STARTUP_GUIDE.md) - 项目启动和部署指南

### 🧪 测试文档
- [测试指南](testing/README.md) - 测试策略和方法
- [API测试报告](testing/api_test_report.md) - API测试结果

### 👨‍💻 开发文档
- [贡献指南](development/CONTRIBUTING.md) - 如何参与项目开发
- [开发工作流](development/WORKFLOW.md) - 开发流程和规范
- [开发日志](development/DEVLOG.md) - 开发过程记录
- [任务管理](development/TASKS.md) - 任务和待办事项

### 🔧 脚本和工具
- [脚本维护计划](SCRIPTS_MAINTENANCE_PLAN.md) - 脚本管理和维护
- [脚本维护摘要](SCRIPTS_MAINTENANCE_SUMMARY.md) - 脚本维护快速指南

### 🐛 修复记录
- [修复文档索引](fixes/README.md) - 所有修复记录的索引
- [UTF-8编码修复](fixes/utf8_encoding_fix.md) - 编码问题修复记录
- [API一致性修复](fixes/endpoint_consistency_fix_summary.md) - API一致性问题修复

### 📋 项目管理
- [项目重组报告](PROJECT_REORGANIZATION_REPORT.md) - 项目结构重组记录
- [实现摘要](implementation_summary.md) - 项目实现概述
- [统一文档API摘要](UNIFIED_DOCUMENT_API_SUMMARY.md) - 文档API统一说明

## 📝 文档维护

### 文档更新规范
1. 所有文档应包含创建/更新日期
2. 重要变更应在文档顶部添加变更日志
3. 过时的文档应及时更新或归档
4. 新功能必须同步更新相关文档

### 文档分类说明
- **架构文档**: 系统设计和架构相关
- **API文档**: 接口定义和使用说明
- **开发文档**: 开发流程和规范
- **部署文档**: 部署和运维指南
- **测试文档**: 测试策略和报告
- **修复文档**: 问题修复记录（历史参考）

## 🔄 最后更新
- 更新日期: {update_date}
- 更新内容: 创建文档索引和导航结构
"""
        
        # 写入更新的README.md
        readme_path = self.docs_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(index_content.format(update_date=datetime.now().strftime("%Y-%m-%d")))
        
        print(f"   ✅ 文档索引已更新: {readme_path}")
    
    def generate_report(self) -> Dict:
        """生成分析报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "analysis_results": self.analysis_results,
            "summary": {
                "total_documents": len(list(self.docs_dir.rglob("*.md"))),
                "merge_candidates": len(self.analysis_results["merge_candidates"]),
                "outdated_documents": len(self.analysis_results["outdated_docs"]),
                "duplicate_documents": len(self.analysis_results["duplicate_docs"]),
                "format_issues": len(self.analysis_results["format_issues"]),
                "recommendations": len(self.analysis_results["recommendations"])
            }
        }
    
    def run_analysis(self) -> Dict:
        """运行完整分析"""
        print("🚀 开始文档组织分析...")
        print(f"📁 文档目录: {self.docs_dir}")
        print()
        
        # 运行各项分析
        self.analyze_fix_documents()
        self.check_document_freshness()
        self.analyze_document_structure()
        self.find_duplicate_content()
        self.generate_recommendations()
        
        # 创建文档索引
        self.create_documentation_index()
        
        # 生成报告
        report = self.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("📊 文档分析结果摘要")
        print("="*60)
        
        summary = report["summary"]
        print(f"📄 总文档数: {summary['total_documents']}")
        print(f"🔄 合并候选: {summary['merge_candidates']} 组")
        print(f"⏰ 过时文档: {summary['outdated_documents']} 个")
        print(f"📋 重复文档: {summary['duplicate_documents']} 组")
        print(f"🎨 格式问题: {summary['format_issues']} 个")
        print(f"💡 建议数量: {summary['recommendations']} 条")
        
        # 显示主要建议
        if self.analysis_results["recommendations"]:
            print("\n💡 主要建议:")
            for i, rec in enumerate(self.analysis_results["recommendations"][:5], 1):
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                emoji = priority_emoji.get(rec["priority"], "⚪")
                print(f"  {i}. {emoji} [{rec['type'].upper()}] {rec['description']}")
        
        # 保存报告
        report_file = self.project_root / "temp" / "documentation_analysis_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return report


def main():
    """主函数"""
    # 获取项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # 假设脚本在 scripts/tools/ 目录中
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
    
    # 运行分析
    organizer = DocumentationOrganizer(project_root)
    report = organizer.run_analysis()
    
    # 设置退出码
    sys.exit(0)


if __name__ == "__main__":
    main()
