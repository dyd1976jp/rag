#!/usr/bin/env python
"""
RAG测试运行脚本
用于运行RAG相关的测试
"""
import os
import sys
import pytest
import argparse
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_tests(test_path=None, verbose=False, capture=True, junit_xml=None, 
              coverage=False, parallel=False, markers=None):
    """
    运行测试
    
    Args:
        test_path: 测试路径，如果为None则运行所有RAG相关测试
        verbose: 是否显示详细输出
        capture: 是否捕获输出
        junit_xml: JUnit XML报告路径
        coverage: 是否生成覆盖率报告
        parallel: 是否并行运行测试
        markers: 指定要运行的测试标记
    """
    # 如果未指定测试路径，则默认运行所有RAG相关测试
    if test_path is None:
        test_path = "services/test_*rag*.py services/test_*cache*.py services/test_*embedding*.py services/test_*retrieval*.py services/test_*custom_exceptions*.py rag/"
    
    # 构建pytest参数
    pytest_args = [test_path]
    
    # 添加详细输出参数
    if verbose:
        pytest_args.append("-v")
    
    # 是否捕获输出
    if not capture:
        pytest_args.append("-s")
    
    # 添加JUnit XML报告
    if junit_xml:
        pytest_args.extend(["--junitxml", junit_xml])
    
    # 添加覆盖率报告
    if coverage:
        pytest_args.extend(["--cov=app.rag", "--cov-report=term", "--cov-report=html:coverage_html"])
    
    # 添加并行运行
    if parallel:
        pytest_args.append("-xvs")
    
    # 添加测试标记
    if markers:
        pytest_args.append(f"-m {markers}")
    
    # 添加颜色输出
    pytest_args.append("--color=yes")
    
    # 运行测试
    logger.info(f"开始运行测试: {test_path}")
    start_time = datetime.now()
    
    exit_code = pytest.main(pytest_args)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"测试完成，耗时 {duration:.2f} 秒，退出码: {exit_code}")
    
    # 如果生成了覆盖率报告，显示覆盖率摘要
    if coverage:
        logger.info("覆盖率报告已生成在 coverage_html 目录中")
    
    return exit_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG测试运行脚本")
    parser.add_argument(
        "--test-path",
        help="测试路径，默认为所有RAG相关测试"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    parser.add_argument(
        "-s", "--no-capture",
        action="store_true",
        help="不捕获输出"
    )
    parser.add_argument(
        "--junit-xml",
        help="JUnit XML报告路径"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="并行运行测试"
    )
    parser.add_argument(
        "-m", "--markers",
        help="指定要运行的测试标记，例如：'slow' 或 'not slow'"
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="只运行缓存相关测试"
    )
    parser.add_argument(
        "--embedding",
        action="store_true",
        help="只运行嵌入模型相关测试"
    )
    parser.add_argument(
        "--retrieval",
        action="store_true",
        help="只运行检索相关测试"
    )
    parser.add_argument(
        "--exceptions",
        action="store_true",
        help="只运行异常处理相关测试"
    )
    parser.add_argument(
        "--rag-func",
        action="store_true",
        help="只运行RAG功能测试"
    )
    
    args = parser.parse_args()
    
    # 处理特定测试类型
    if args.cache:
        args.test_path = "services/test_cache_service.py"
    elif args.embedding:
        args.test_path = "services/test_embedding_model.py"
    elif args.retrieval:
        args.test_path = "services/test_retrieval_service.py"
    elif args.exceptions:
        args.test_path = "services/test_custom_exceptions.py"
    elif args.rag_func:
        args.test_path = "rag/"
    
    # 运行测试
    exit_code = run_tests(
        test_path=args.test_path,
        verbose=args.verbose,
        capture=not args.no_capture,
        junit_xml=args.junit_xml,
        coverage=args.coverage,
        parallel=args.parallel,
        markers=args.markers
    )
    
    # 退出码
    sys.exit(exit_code) 