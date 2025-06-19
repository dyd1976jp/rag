#!/usr/bin/env python3
"""
重组后的测试运行脚本

提供便捷的测试运行接口，支持按类型、标记运行测试。
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        """初始化测试运行器"""
        self.base_cmd = ["python", "-m", "pytest"]
        self.test_dir = Path(__file__).parent
    
    def run_unit_tests(self, verbose: bool = False) -> int:
        """
        运行单元测试
        
        Args:
            verbose: 是否显示详细输出
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd + ["unit/", "-m", "unit"]
        if verbose:
            cmd.append("-v")
        
        print("🧪 运行单元测试...")
        return self._execute_command(cmd)
    
    def run_integration_tests(self, verbose: bool = False) -> int:
        """
        运行集成测试
        
        Args:
            verbose: 是否显示详细输出
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd + ["integration/", "-m", "integration"]
        if verbose:
            cmd.append("-v")
        
        print("🔗 运行集成测试...")
        return self._execute_command(cmd)
    
    def run_api_tests(self, verbose: bool = False) -> int:
        """
        运行API测试
        
        Args:
            verbose: 是否显示详细输出
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd + ["-m", "api"]
        if verbose:
            cmd.append("-v")
        
        print("🌐 运行API测试...")
        return self._execute_command(cmd)
    
    def run_document_tests(self, verbose: bool = False) -> int:
        """
        运行文档相关测试
        
        Args:
            verbose: 是否显示详细输出
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd + ["-m", "document"]
        if verbose:
            cmd.append("-v")
        
        print("📄 运行文档测试...")
        return self._execute_command(cmd)
    
    def run_all_tests(self, verbose: bool = False, coverage: bool = False) -> int:
        """
        运行所有测试
        
        Args:
            verbose: 是否显示详细输出
            coverage: 是否生成覆盖率报告
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd.copy()
        
        if coverage:
            cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
        
        if verbose:
            cmd.append("-v")
        
        print("🚀 运行所有测试...")
        return self._execute_command(cmd)
    
    def run_specific_test(self, test_path: str, verbose: bool = False) -> int:
        """
        运行特定测试
        
        Args:
            test_path: 测试文件路径
            verbose: 是否显示详细输出
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd + [test_path]
        if verbose:
            cmd.append("-v")
        
        print(f"🎯 运行特定测试: {test_path}")
        return self._execute_command(cmd)
    
    def run_by_keyword(self, keyword: str, verbose: bool = False) -> int:
        """
        按关键词运行测试
        
        Args:
            keyword: 关键词
            verbose: 是否显示详细输出
            
        Returns:
            int: 退出代码
        """
        cmd = self.base_cmd + ["-k", keyword]
        if verbose:
            cmd.append("-v")
        
        print(f"🔍 运行包含关键词 '{keyword}' 的测试...")
        return self._execute_command(cmd)
    
    def _execute_command(self, cmd: List[str]) -> int:
        """
        执行命令
        
        Args:
            cmd: 命令列表
            
        Returns:
            int: 退出代码
        """
        print(f"执行命令: {' '.join(cmd)}")
        print("=" * 80)
        
        try:
            # 切换到测试目录
            os.chdir(self.test_dir)
            result = subprocess.run(cmd)
            return result.returncode
        except KeyboardInterrupt:
            print("\n测试被用户中断")
            return 130
        except Exception as e:
            print(f"执行测试时出错: {e}")
            return 1


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='RAG-Chat 重组测试运行工具')
    
    # 测试类型选择
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--unit', action='store_true', help='运行单元测试')
    test_group.add_argument('--integration', action='store_true', help='运行集成测试')
    test_group.add_argument('--api', action='store_true', help='运行API测试')
    test_group.add_argument('--document', action='store_true', help='运行文档测试')
    test_group.add_argument('--all', action='store_true', help='运行所有测试')
    
    # 特定测试
    parser.add_argument('--file', '-f', help='运行特定测试文件')
    parser.add_argument('--keyword', '-k', help='按关键词运行测试')
    
    # 选项
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--coverage', '-c', action='store_true', help='生成覆盖率报告')
    
    return parser.parse_args()


def print_help() -> None:
    """打印帮助信息"""
    print("\n🧪 RAG-Chat 重组测试运行工具")
    print("\n📋 使用示例:")
    print("  python run_organized_tests.py --unit              # 运行单元测试")
    print("  python run_organized_tests.py --integration       # 运行集成测试")
    print("  python run_organized_tests.py --api               # 运行API测试")
    print("  python run_organized_tests.py --document          # 运行文档测试")
    print("  python run_organized_tests.py --all --coverage    # 运行所有测试并生成覆盖率")
    print("  python run_organized_tests.py --file unit/test_document_splitter.py  # 运行特定文件")
    print("  python run_organized_tests.py --keyword split     # 运行包含'split'的测试")
    
    print("\n🏷️  测试标记:")
    print("  @pytest.mark.unit         - 单元测试")
    print("  @pytest.mark.integration  - 集成测试")
    print("  @pytest.mark.api          - API测试")
    print("  @pytest.mark.document     - 文档测试")
    print("  @pytest.mark.slow         - 慢速测试")
    
    print("\n📁 测试目录结构:")
    print("  unit/                     - 单元测试")
    print("  integration/              - 集成测试")
    print("  fixtures/                 - 测试数据")
    print("  utils/                    - 测试工具")
    
    print("\n更多选项请运行: python run_organized_tests.py --help")
    print("=" * 80)


def main() -> int:
    """
    主函数
    
    Returns:
        int: 退出代码
    """
    # 检查是否在正确的目录
    if not Path('conftest.py').exists():
        print("❌ 错误: 请在tests目录中运行此脚本")
        print(f"当前目录: {os.getcwd()}")
        print("用法: cd backend/tests && python run_organized_tests.py")
        return 1
    
    args = parse_args()
    runner = TestRunner()
    
    # 如果没有提供参数，显示帮助
    if len(sys.argv) == 1:
        print_help()
        return 0
    
    # 根据参数运行相应的测试
    if args.unit:
        return runner.run_unit_tests(args.verbose)
    elif args.integration:
        return runner.run_integration_tests(args.verbose)
    elif args.api:
        return runner.run_api_tests(args.verbose)
    elif args.document:
        return runner.run_document_tests(args.verbose)
    elif args.all:
        return runner.run_all_tests(args.verbose, args.coverage)
    elif args.file:
        return runner.run_specific_test(args.file, args.verbose)
    elif args.keyword:
        return runner.run_by_keyword(args.keyword, args.verbose)
    else:
        print("❌ 请指定要运行的测试类型")
        print("使用 --help 查看可用选项")
        return 1


if __name__ == '__main__':
    sys.exit(main())
