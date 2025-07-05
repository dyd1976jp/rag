#!/usr/bin/env python3
"""
文件结构合规性验证脚本

根据PLANNING.md中定义的文件组织规范，验证项目文件结构的合规性。
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime


class FileStructureValidator:
    """文件结构验证器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations = []
        self.warnings = []
        
    def validate_root_directory(self) -> bool:
        """验证根目录结构"""
        print("🔍 验证根目录结构...")
        
        # 应该存在的核心文件
        required_files = [
            "README.md",
            "PLANNING.md", 
            "TASK.md",
            "pyproject.toml",
            "docker-compose.yml",
            "Dockerfile",
            ".env.example"
        ]
        
        # 应该存在的核心目录
        required_dirs = [
            "backend",
            "frontend-app",
            "data",
            "docs",
            "scripts",
            "temp",
            "logs"
        ]
        
        # 不应该存在的文件模式
        forbidden_patterns = [
            "test_*.py",
            "debug_*.html",
            "fix_*.py",
            "*_fix_*.txt",
            "*.json"  # API响应文件等
        ]
        
        violations = []
        
        # 检查必需文件
        for file in required_files:
            if not (self.project_root / file).exists():
                violations.append(f"缺少必需文件: {file}")
        
        # 检查必需目录
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).is_dir():
                violations.append(f"缺少必需目录: {dir_name}")
        
        # 检查禁止的文件模式
        for item in self.project_root.iterdir():
            if item.is_file():
                for pattern in forbidden_patterns:
                    if self._matches_pattern(item.name, pattern):
                        violations.append(f"根目录包含应移动的文件: {item.name}")
        
        self.violations.extend(violations)
        return len(violations) == 0
    
    def validate_backend_structure(self) -> bool:
        """验证后端目录结构"""
        print("🔍 验证后端目录结构...")
        
        backend_dir = self.project_root / "backend"
        if not backend_dir.exists():
            self.violations.append("backend目录不存在")
            return False
        
        # 应该存在的后端子目录
        required_subdirs = [
            "app",
            "tests", 
            "database",
            "scripts"
        ]
        
        violations = []
        
        for subdir in required_subdirs:
            if not (backend_dir / subdir).is_dir():
                violations.append(f"backend缺少子目录: {subdir}")
        
        # 检查app目录结构
        app_dir = backend_dir / "app"
        if app_dir.exists():
            app_subdirs = ["api", "core", "models", "services", "rag", "db"]
            for subdir in app_subdirs:
                if not (app_dir / subdir).is_dir():
                    self.warnings.append(f"backend/app缺少推荐子目录: {subdir}")
        
        self.violations.extend(violations)
        return len(violations) == 0
    
    def validate_test_structure(self) -> bool:
        """验证测试目录结构"""
        print("🔍 验证测试目录结构...")
        
        tests_dir = self.project_root / "backend" / "tests"
        if not tests_dir.exists():
            self.violations.append("backend/tests目录不存在")
            return False
        
        # 推荐的测试子目录
        recommended_subdirs = [
            "unit",
            "integration", 
            "performance",
            "fixtures",
            "mocks",
            "utils"
        ]
        
        for subdir in recommended_subdirs:
            if not (tests_dir / subdir).is_dir():
                self.warnings.append(f"tests缺少推荐子目录: {subdir}")
        
        return True
    
    def validate_docs_structure(self) -> bool:
        """验证文档目录结构"""
        print("🔍 验证文档目录结构...")
        
        docs_dir = self.project_root / "docs"
        if not docs_dir.exists():
            self.violations.append("docs目录不存在")
            return False
        
        # 推荐的文档子目录
        recommended_subdirs = [
            "api",
            "development",
            "deployment", 
            "testing",
            "fixes"
        ]
        
        for subdir in recommended_subdirs:
            if not (docs_dir / subdir).is_dir():
                self.warnings.append(f"docs缺少推荐子目录: {subdir}")
        
        return True
    
    def validate_scripts_structure(self) -> bool:
        """验证脚本目录结构"""
        print("🔍 验证脚本目录结构...")
        
        scripts_dir = self.project_root / "scripts"
        if not scripts_dir.exists():
            self.violations.append("scripts目录不存在")
            return False
        
        # 推荐的脚本子目录
        recommended_subdirs = [
            "backend",
            "database",
            "deployment",
            "testing",
            "tools"
        ]
        
        for subdir in recommended_subdirs:
            if not (scripts_dir / subdir).is_dir():
                self.warnings.append(f"scripts缺少推荐子目录: {subdir}")
        
        return True
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """简单的模式匹配"""
        if pattern.startswith("*") and pattern.endswith("*"):
            return pattern[1:-1] in filename
        elif pattern.startswith("*"):
            return filename.endswith(pattern[1:])
        elif pattern.endswith("*"):
            return filename.startswith(pattern[:-1])
        else:
            return filename == pattern
    
    def generate_report(self) -> Dict:
        """生成验证报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "violations": self.violations,
            "warnings": self.warnings,
            "total_violations": len(self.violations),
            "total_warnings": len(self.warnings),
            "is_compliant": len(self.violations) == 0
        }
    
    def run_validation(self) -> bool:
        """运行完整验证"""
        print("🚀 开始文件结构合规性验证...")
        print(f"📁 项目根目录: {self.project_root}")
        print()
        
        # 运行各项验证
        validations = [
            self.validate_root_directory(),
            self.validate_backend_structure(),
            self.validate_test_structure(),
            self.validate_docs_structure(),
            self.validate_scripts_structure()
        ]
        
        # 生成报告
        report = self.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("📊 验证结果摘要")
        print("="*60)
        
        if report["is_compliant"]:
            print("✅ 文件结构完全合规！")
        else:
            print(f"❌ 发现 {report['total_violations']} 个违规项")
        
        if report["total_warnings"] > 0:
            print(f"⚠️  发现 {report['total_warnings']} 个警告项")
        
        # 输出详细信息
        if self.violations:
            print("\n🚨 违规项:")
            for i, violation in enumerate(self.violations, 1):
                print(f"  {i}. {violation}")
        
        if self.warnings:
            print("\n⚠️  警告项:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        # 保存报告
        report_file = self.project_root / "temp" / "file_structure_validation_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return report["is_compliant"]


def main():
    """主函数"""
    # 获取项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # 假设脚本在 scripts/tools/ 目录中
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
    
    # 运行验证
    validator = FileStructureValidator(project_root)
    is_compliant = validator.run_validation()
    
    # 设置退出码
    sys.exit(0 if is_compliant else 1)


if __name__ == "__main__":
    main()
