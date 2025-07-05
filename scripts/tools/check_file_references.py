#!/usr/bin/env python3
"""
文件引用完整性检查脚本

检查项目中的文件引用是否完整，包括：
- Python import语句
- 配置文件路径引用
- 文档中的文件路径引用
- 脚本中的文件路径引用
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json
from datetime import datetime


class FileReferenceChecker:
    """文件引用检查器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.broken_references = []
        self.warnings = []
        
    def find_python_imports(self) -> List[Tuple[str, str, int]]:
        """查找Python文件中的import语句"""
        imports = []
        
        # 查找所有Python文件
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 查找import语句
                import_patterns = [
                    r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',
                    r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
                ]
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in import_patterns:
                        matches = re.findall(pattern, line)
                        for match in matches:
                            imports.append((str(py_file), match, line_num))
                            
            except Exception as e:
                self.warnings.append(f"无法读取文件 {py_file}: {e}")
        
        return imports
    
    def find_file_path_references(self) -> List[Tuple[str, str, int]]:
        """查找文件路径引用"""
        references = []
        
        # 查找配置文件、脚本文件、文档文件
        file_patterns = ["*.py", "*.md", "*.yml", "*.yaml", "*.json", "*.sh"]
        
        for pattern in file_patterns:
            for file_path in self.project_root.rglob(pattern):
                if "venv" in str(file_path) or "__pycache__" in str(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 查找文件路径引用模式
                    path_patterns = [
                        r'["\']([^"\']*\.py)["\']',  # Python文件引用
                        r'["\']([^"\']*\.md)["\']',  # Markdown文件引用
                        r'["\']([^"\']*\.json)["\']',  # JSON文件引用
                        r'["\']([^"\']*\.yml)["\']',  # YAML文件引用
                        r'["\']([^"\']*\.yaml)["\']',  # YAML文件引用
                        r'["\']([^"\']*\.sh)["\']',  # Shell脚本引用
                        r'["\']([^"\']*\.txt)["\']',  # 文本文件引用
                    ]
                    
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for pattern in path_patterns:
                            matches = re.findall(pattern, line)
                            for match in matches:
                                if not match.startswith('http') and '/' in match:
                                    references.append((str(file_path), match, line_num))
                                    
                except Exception as e:
                    self.warnings.append(f"无法读取文件 {file_path}: {e}")
        
        return references
    
    def check_reference_validity(self, references: List[Tuple[str, str, int]]) -> None:
        """检查引用的有效性"""
        print("🔍 检查文件引用有效性...")
        
        for source_file, referenced_path, line_num in references:
            source_path = Path(source_file)
            
            # 尝试不同的路径解析方式
            possible_paths = [
                self.project_root / referenced_path,  # 相对于项目根目录
                source_path.parent / referenced_path,  # 相对于源文件目录
                Path(referenced_path),  # 绝对路径
            ]
            
            # 检查是否存在
            exists = any(path.exists() for path in possible_paths)
            
            if not exists:
                self.broken_references.append({
                    "source_file": str(source_path.relative_to(self.project_root)),
                    "referenced_path": referenced_path,
                    "line_number": line_num,
                    "possible_paths": [str(p) for p in possible_paths]
                })
    
    def check_import_validity(self, imports: List[Tuple[str, str, int]]) -> None:
        """检查Python import的有效性"""
        print("🔍 检查Python import有效性...")
        
        for source_file, import_module, line_num in imports:
            source_path = Path(source_file)
            
            # 跳过标准库和第三方库
            if self._is_standard_or_third_party_module(import_module):
                continue
            
            # 检查相对import
            if import_module.startswith('.'):
                continue  # 相对import比较复杂，暂时跳过
            
            # 检查项目内模块
            module_parts = import_module.split('.')
            
            # 尝试找到对应的Python文件或包
            possible_paths = []
            
            # 从项目根目录开始查找
            current_path = self.project_root
            for part in module_parts:
                current_path = current_path / part
                possible_paths.append(current_path.with_suffix('.py'))
                possible_paths.append(current_path / '__init__.py')
            
            # 从backend目录开始查找（如果存在）
            if (self.project_root / 'backend').exists():
                current_path = self.project_root / 'backend'
                for part in module_parts:
                    current_path = current_path / part
                    possible_paths.append(current_path.with_suffix('.py'))
                    possible_paths.append(current_path / '__init__.py')
            
            # 检查是否存在
            exists = any(path.exists() for path in possible_paths)
            
            if not exists and not self._is_likely_external_module(import_module):
                self.broken_references.append({
                    "source_file": str(source_path.relative_to(self.project_root)),
                    "referenced_path": import_module,
                    "line_number": line_num,
                    "type": "python_import",
                    "possible_paths": [str(p) for p in possible_paths if p.exists()]
                })
    
    def _is_standard_or_third_party_module(self, module_name: str) -> bool:
        """判断是否为标准库或第三方库模块"""
        standard_modules = {
            'os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 're', 
            'asyncio', 'logging', 'unittest', 'pytest', 'fastapi', 
            'pydantic', 'pymongo', 'pymilvus', 'openai', 'langchain',
            'uvicorn', 'redis', 'motor', 'bcrypt', 'jose', 'passlib'
        }
        
        root_module = module_name.split('.')[0]
        return root_module in standard_modules
    
    def _is_likely_external_module(self, module_name: str) -> bool:
        """判断是否可能是外部模块"""
        # 如果模块名不包含项目特定的前缀，可能是外部模块
        project_prefixes = ['app', 'backend', 'rag', 'services', 'models']
        root_module = module_name.split('.')[0]
        return root_module not in project_prefixes
    
    def generate_report(self) -> Dict:
        """生成检查报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "broken_references": self.broken_references,
            "warnings": self.warnings,
            "total_broken_references": len(self.broken_references),
            "total_warnings": len(self.warnings),
            "is_valid": len(self.broken_references) == 0
        }
    
    def run_check(self) -> bool:
        """运行完整检查"""
        print("🚀 开始文件引用完整性检查...")
        print(f"📁 项目根目录: {self.project_root}")
        print()
        
        # 查找引用
        print("🔍 查找Python import语句...")
        imports = self.find_python_imports()
        print(f"   找到 {len(imports)} 个import语句")
        
        print("🔍 查找文件路径引用...")
        references = self.find_file_path_references()
        print(f"   找到 {len(references)} 个文件路径引用")
        
        # 检查有效性
        self.check_import_validity(imports)
        self.check_reference_validity(references)
        
        # 生成报告
        report = self.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("📊 检查结果摘要")
        print("="*60)
        
        if report["is_valid"]:
            print("✅ 所有文件引用都有效！")
        else:
            print(f"❌ 发现 {report['total_broken_references']} 个无效引用")
        
        if report["total_warnings"] > 0:
            print(f"⚠️  发现 {report['total_warnings']} 个警告")
        
        # 输出详细信息
        if self.broken_references:
            print("\n🚨 无效引用:")
            for i, ref in enumerate(self.broken_references, 1):
                print(f"  {i}. {ref['source_file']}:{ref['line_number']}")
                print(f"     引用: {ref['referenced_path']}")
                if ref.get('type') == 'python_import':
                    print(f"     类型: Python import")
        
        if self.warnings:
            print("\n⚠️  警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        # 保存报告
        report_file = self.project_root / "temp" / "file_references_check_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return report["is_valid"]


def main():
    """主函数"""
    # 获取项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # 假设脚本在 scripts/tools/ 目录中
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
    
    # 运行检查
    checker = FileReferenceChecker(project_root)
    is_valid = checker.run_check()
    
    # 设置退出码
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
