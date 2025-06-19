#!/usr/bin/env python
"""
测试运行脚本

用于方便地运行不同类型的测试，可以指定特定模块、标记或测试文件。
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import Any

def parse_args() -> argparse.Namespace:
    """
    解析命令行参数

    Returns:
        argparse.Namespace: 解析后的命令行参数
    """
    parser = argparse.ArgumentParser(description='RAG-Chat 测试运行工具')
    parser.add_argument('--module', '-m', help='要测试的模块 (api, db, discover, services)', default=None)
    parser.add_argument('--file', '-f', help='要测试的文件路径', default=None)
    parser.add_argument('--mark', '-k', help='测试标记或关键字', default=None)
    parser.add_argument('--verbose', '-v', action='count', default=0, help='详细程度 (-v 或 -vv)')
    parser.add_argument('--pdb', action='store_true', help='失败时进入调试器')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default=None, help='日志级别')
    return parser.parse_args()

def run_tests(args: argparse.Namespace) -> int:
    """
    运行测试

    Args:
        args: 命令行参数

    Returns:
        int: 退出代码
    """
    # 确保我们在backend目录中
    if not Path('app').exists() or not Path('tests').exists():
        print("\n错误: 请在backend目录中运行此脚本")
        print("当前目录:", os.getcwd())
        print("用法: cd /path/to/RAG-chat/backend && python tests/run_tests.py\n")
        return 1
    
    # 构建命令
    cmd = ['python', '-m', 'pytest']
    
    # 添加详细程度
    if args.verbose > 0:
        cmd.append('-' + 'v' * args.verbose)
    
    # 添加PDB支持
    if args.pdb:
        cmd.append('--pdb')
    
    # 添加日志级别
    if args.log_level:
        cmd.append(f'--log-cli-level={args.log_level}')
    
    # 添加模块路径
    if args.module:
        module_path = f'tests/{args.module}/'
        if not Path(module_path).exists():
            print(f"\n错误: 模块 '{args.module}' 不存在")
            print(f"有效模块: api, db, discover, services\n")
            return 1
        cmd.append(module_path)
    
    # 添加文件路径
    if args.file:
        file_path = args.file
        if not file_path.startswith('tests/'):
            file_path = f'tests/{file_path}'
        if not Path(file_path).exists():
            print(f"\n错误: 文件 '{file_path}' 不存在\n")
            return 1
        cmd.append(file_path)
    
    # 添加标记
    if args.mark:
        cmd.append(f'-k {args.mark}')
    
    # 打印命令
    cmd_str = ' '.join(cmd)
    print(f"\n运行测试命令: {cmd_str}\n")
    print("=" * 80)
    
    # 运行命令
    try:
        result = subprocess.run(cmd_str, shell=True)
        return result.returncode
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 130

def print_help() -> None:
    """
    打印帮助信息
    """
    print("\nRAG-Chat 测试运行工具")
    print("\n用法示例:")
    print("  python tests/run_tests.py                     # 运行所有测试")
    print("  python tests/run_tests.py --module discover   # 运行模型发现测试")
    print("  python tests/run_tests.py --file test_llm_endpoints.py  # 运行特定文件")
    print("  python tests/run_tests.py -v -k \"discover\"   # 运行名称包含discover的测试")
    print("  python tests/run_tests.py --log-level INFO    # 设置日志级别")
    print("\n更多选项请运行: python tests/run_tests.py --help")
    print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print_help()
    args = parse_args()
    sys.exit(run_tests(args)) 