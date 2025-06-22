#!/usr/bin/env python3
"""
统一的测试运行脚本

整合了原来的多个测试运行脚本，提供统一的测试执行入口。
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并处理结果"""
    print(f"\n{'='*60}")
    if description:
        print(f"执行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description or '命令'} 执行成功")
        else:
            print(f"❌ {description or '命令'} 执行失败 (返回码: {result.returncode})")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="RAG系统测试运行器")
    
    # 测试类型选项
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    
    # 特定模块测试
    parser.add_argument("--api", action="store_true", help="运行API测试")
    parser.add_argument("--rag", action="store_true", help="运行RAG功能测试")
    parser.add_argument("--services", action="store_true", help="运行服务层测试")
    parser.add_argument("--db", action="store_true", help="运行数据库测试")
    
    # 测试选项
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--parallel", action="store_true", help="并行运行测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--test-path", help="指定测试路径")
    
    # 特定测试（兼容旧脚本）
    parser.add_argument("--cache", action="store_true", help="运行缓存服务测试")
    parser.add_argument("--embedding", action="store_true", help="运行嵌入模型测试")
    parser.add_argument("--retrieval", action="store_true", help="运行检索服务测试")
    parser.add_argument("--exceptions", action="store_true", help="运行异常处理测试")
    
    args = parser.parse_args()
    
    # 构建pytest命令
    pytest_cmd = ["python", "-m", "pytest"]
    
    # 添加详细输出
    if args.verbose:
        pytest_cmd.append("-v")
    
    # 添加并行选项
    if args.parallel:
        pytest_cmd.extend(["-n", "auto"])
    
    # 添加覆盖率选项
    if args.coverage:
        pytest_cmd.extend([
            "--cov=app",
            "--cov-report=html:coverage_html",
            "--cov-report=term-missing"
        ])
    
    success_count = 0
    total_count = 0
    
    # 根据参数选择测试
    if args.all:
        total_count += 1
        if run_command(pytest_cmd + ["."], "运行所有测试"):
            success_count += 1
    
    elif args.unit:
        total_count += 1
        if run_command(pytest_cmd + ["unit/"], "运行单元测试"):
            success_count += 1
    
    elif args.integration:
        total_count += 1
        if run_command(pytest_cmd + ["integration/"], "运行集成测试"):
            success_count += 1
    
    elif args.performance:
        total_count += 1
        if run_command(pytest_cmd + ["performance/"], "运行性能测试"):
            success_count += 1
    
    elif args.api:
        total_count += 1
        if run_command(pytest_cmd + ["unit/api/"], "运行API测试"):
            success_count += 1
    
    elif args.rag:
        total_count += 1
        if run_command(pytest_cmd + ["unit/rag/"], "运行RAG功能测试"):
            success_count += 1
    
    elif args.services:
        total_count += 1
        if run_command(pytest_cmd + ["unit/services/"], "运行服务层测试"):
            success_count += 1
    
    elif args.db:
        total_count += 1
        if run_command(pytest_cmd + ["unit/db/"], "运行数据库测试"):
            success_count += 1
    
    elif args.test_path:
        total_count += 1
        if run_command(pytest_cmd + [args.test_path], f"运行指定路径测试: {args.test_path}"):
            success_count += 1
    
    # 兼容旧脚本的特定测试
    elif args.cache:
        total_count += 1
        if run_command(pytest_cmd + ["unit/services/test_cache_service.py"], "运行缓存服务测试"):
            success_count += 1
    
    elif args.embedding:
        total_count += 1
        if run_command(pytest_cmd + ["unit/services/test_embedding_model.py"], "运行嵌入模型测试"):
            success_count += 1
    
    elif args.retrieval:
        total_count += 1
        if run_command(pytest_cmd + ["unit/services/test_retrieval_service.py"], "运行检索服务测试"):
            success_count += 1
    
    elif args.exceptions:
        total_count += 1
        if run_command(pytest_cmd + ["unit/services/test_custom_exceptions.py"], "运行异常处理测试"):
            success_count += 1
    
    else:
        # 默认运行所有测试
        total_count += 1
        if run_command(pytest_cmd + ["."], "运行所有测试（默认）"):
            success_count += 1
    
    # 输出总结
    print(f"\n{'='*60}")
    print("测试执行总结")
    print('='*60)
    print(f"总测试组: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {total_count - success_count}")
    
    if success_count == total_count:
        print("🎉 所有测试都执行成功！")
        sys.exit(0)
    else:
        print("❌ 部分测试执行失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
