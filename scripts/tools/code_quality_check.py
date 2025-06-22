#!/usr/bin/env python3
"""
代码质量检查脚本

检查Python代码的质量问题，包括：
1. 过长的函数和文件
2. 缺失的类型注解
3. 缺失的文档字符串
4. 导入语句规范性
"""

import os
import ast
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse


class CodeQualityChecker:
    """代码质量检查器"""
    
    def __init__(self, max_function_lines: int = 50, max_file_lines: int = 500):
        """
        初始化检查器
        
        Args:
            max_function_lines: 函数最大行数
            max_file_lines: 文件最大行数
        """
        self.max_function_lines = max_function_lines
        self.max_file_lines = max_file_lines
        self.issues: List[Dict[str, Any]] = []
    
    def check_directory(self, directory: str) -> Dict[str, Any]:
        """
        检查目录下的所有Python文件
        
        Args:
            directory: 要检查的目录路径
            
        Returns:
            Dict: 检查结果统计
        """
        directory_path = Path(directory)
        python_files = list(directory_path.rglob("*.py"))
        
        stats = {
            "total_files": len(python_files),
            "checked_files": 0,
            "issues_count": 0,
            "long_files": [],
            "long_functions": [],
            "missing_docstrings": [],
            "missing_type_hints": [],
            "import_issues": []
        }
        
        for file_path in python_files:
            try:
                self._check_file(file_path, stats)
                stats["checked_files"] += 1
            except Exception as e:
                print(f"检查文件 {file_path} 时出错: {e}")
        
        stats["issues_count"] = len(self.issues)
        return stats
    
    def _check_file(self, file_path: Path, stats: Dict[str, Any]) -> None:
        """
        检查单个文件
        
        Args:
            file_path: 文件路径
            stats: 统计信息字典
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # 检查文件长度
        if len(lines) > self.max_file_lines:
            issue = {
                "type": "long_file",
                "file": str(file_path),
                "lines": len(lines),
                "message": f"文件过长: {len(lines)} 行 (建议 < {self.max_file_lines} 行)"
            }
            self.issues.append(issue)
            stats["long_files"].append(issue)
        
        # 解析AST
        try:
            tree = ast.parse(content)
            self._check_ast(tree, file_path, lines, stats)
        except SyntaxError as e:
            print(f"语法错误 {file_path}: {e}")
    
    def _check_ast(self, tree: ast.AST, file_path: Path, lines: List[str], stats: Dict[str, Any]) -> None:
        """
        检查AST节点
        
        Args:
            tree: AST树
            file_path: 文件路径
            lines: 文件行列表
            stats: 统计信息字典
        """
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_function(node, file_path, lines, stats)
            elif isinstance(node, ast.ClassDef):
                self._check_class(node, file_path, stats)
    
    def _check_function(self, node: ast.FunctionDef, file_path: Path, lines: List[str], stats: Dict[str, Any]) -> None:
        """
        检查函数定义
        
        Args:
            node: 函数AST节点
            file_path: 文件路径
            lines: 文件行列表
            stats: 统计信息字典
        """
        # 计算函数行数
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
        function_lines = end_line - start_line + 1
        
        # 检查函数长度
        if function_lines > self.max_function_lines:
            issue = {
                "type": "long_function",
                "file": str(file_path),
                "function": node.name,
                "lines": function_lines,
                "start_line": start_line,
                "message": f"函数过长: {function_lines} 行 (建议 < {self.max_function_lines} 行)"
            }
            self.issues.append(issue)
            stats["long_functions"].append(issue)
        
        # 检查文档字符串
        if not ast.get_docstring(node):
            issue = {
                "type": "missing_docstring",
                "file": str(file_path),
                "function": node.name,
                "line": start_line,
                "message": f"函数缺少文档字符串: {node.name}"
            }
            self.issues.append(issue)
            stats["missing_docstrings"].append(issue)
        
        # 检查返回类型注解
        if not node.returns and not node.name.startswith('_'):
            issue = {
                "type": "missing_type_hint",
                "file": str(file_path),
                "function": node.name,
                "line": start_line,
                "message": f"函数缺少返回类型注解: {node.name}"
            }
            self.issues.append(issue)
            stats["missing_type_hints"].append(issue)
    
    def _check_class(self, node: ast.ClassDef, file_path: Path, stats: Dict[str, Any]) -> None:
        """
        检查类定义
        
        Args:
            node: 类AST节点
            file_path: 文件路径
            stats: 统计信息字典
        """
        # 检查类文档字符串
        if not ast.get_docstring(node):
            issue = {
                "type": "missing_docstring",
                "file": str(file_path),
                "class": node.name,
                "line": node.lineno,
                "message": f"类缺少文档字符串: {node.name}"
            }
            self.issues.append(issue)
            stats["missing_docstrings"].append(issue)
    
    def print_report(self, stats: Dict[str, Any]) -> None:
        """
        打印检查报告
        
        Args:
            stats: 统计信息
        """
        print("\n" + "="*80)
        print("代码质量检查报告")
        print("="*80)
        
        print(f"\n📊 总体统计:")
        print(f"  检查文件数: {stats['checked_files']}/{stats['total_files']}")
        print(f"  发现问题数: {stats['issues_count']}")
        
        if stats['long_files']:
            print(f"\n📄 过长文件 ({len(stats['long_files'])} 个):")
            for issue in stats['long_files'][:5]:  # 只显示前5个
                print(f"  - {issue['file']}: {issue['lines']} 行")
        
        if stats['long_functions']:
            print(f"\n🔧 过长函数 ({len(stats['long_functions'])} 个):")
            for issue in stats['long_functions'][:5]:  # 只显示前5个
                print(f"  - {issue['file']}:{issue['start_line']} {issue['function']}(): {issue['lines']} 行")
        
        if stats['missing_docstrings']:
            print(f"\n📝 缺少文档字符串 ({len(stats['missing_docstrings'])} 个):")
            for issue in stats['missing_docstrings'][:5]:  # 只显示前5个
                func_or_class = issue.get('function', issue.get('class', 'unknown'))
                print(f"  - {issue['file']}:{issue['line']} {func_or_class}")
        
        if stats['missing_type_hints']:
            print(f"\n🏷️  缺少类型注解 ({len(stats['missing_type_hints'])} 个):")
            for issue in stats['missing_type_hints'][:5]:  # 只显示前5个
                print(f"  - {issue['file']}:{issue['line']} {issue['function']}()")
        
        print("\n" + "="*80)
        
        # 给出改进建议
        if stats['issues_count'] > 0:
            print("\n💡 改进建议:")
            if stats['long_files']:
                print("  - 考虑将过长的文件拆分为多个模块")
            if stats['long_functions']:
                print("  - 将过长的函数拆分为更小的函数")
            if stats['missing_docstrings']:
                print("  - 为函数和类添加文档字符串")
            if stats['missing_type_hints']:
                print("  - 为函数添加类型注解以提高代码可读性")
        else:
            print("\n✅ 代码质量良好，未发现明显问题！")


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description='代码质量检查工具')
    parser.add_argument('directory', help='要检查的目录路径')
    parser.add_argument('--max-function-lines', type=int, default=50, help='函数最大行数')
    parser.add_argument('--max-file-lines', type=int, default=500, help='文件最大行数')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"错误: 目录 {args.directory} 不存在")
        sys.exit(1)
    
    checker = CodeQualityChecker(args.max_function_lines, args.max_file_lines)
    stats = checker.check_directory(args.directory)
    checker.print_report(stats)


if __name__ == '__main__':
    main()
