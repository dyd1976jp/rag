#!/usr/bin/env python3
"""
CI/CD友好的测试运行脚本

替代shell脚本测试，提供统一的测试入口点
支持不同的测试类型和环境配置
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings


class TestRunner:
    """测试运行器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.backend_dir = backend_dir
        self.tests_dir = self.backend_dir / "tests"
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] {level}: {message}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """运行命令并返回结果"""
        if cwd is None:
            cwd = self.backend_dir
            
        self.log(f"运行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            self.log("命令执行超时", "ERROR")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out"
            }
        except Exception as e:
            self.log(f"命令执行失败: {e}", "ERROR")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    def run_unit_tests(self) -> bool:
        """运行单元测试"""
        self.log("开始运行单元测试")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.tests_dir / "unit"),
            "-v",
            "--tb=short",
            "-m", "unit"
        ]
        
        result = self.run_command(cmd)
        self.results["unit_tests"] = result
        
        if result["success"]:
            self.log("单元测试通过", "INFO")
        else:
            self.log("单元测试失败", "ERROR")
            if self.verbose:
                print(result["stderr"])
        
        return result["success"]
    
    def run_integration_tests(self) -> bool:
        """运行集成测试"""
        self.log("开始运行集成测试")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.tests_dir / "integration"),
            "-v",
            "--tb=short",
            "-m", "integration"
        ]
        
        result = self.run_command(cmd)
        self.results["integration_tests"] = result
        
        if result["success"]:
            self.log("集成测试通过", "INFO")
        else:
            self.log("集成测试失败", "ERROR")
            if self.verbose:
                print(result["stderr"])
        
        return result["success"]
    
    def run_comprehensive_tests(self) -> bool:
        """运行综合测试（替代shell脚本）"""
        self.log("开始运行综合测试")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.tests_dir / "integration/test_api_endpoints_comprehensive.py"),
            str(self.tests_dir / "integration/test_document_upload_comprehensive.py"),
            "-v",
            "--tb=short",
            "-m", "comprehensive"
        ]
        
        result = self.run_command(cmd)
        self.results["comprehensive_tests"] = result
        
        if result["success"]:
            self.log("综合测试通过", "INFO")
        else:
            self.log("综合测试失败", "ERROR")
            if self.verbose:
                print(result["stderr"])
        
        return result["success"]
    
    def run_coverage_tests(self) -> bool:
        """运行覆盖率测试"""
        self.log("开始运行覆盖率测试")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.tests_dir),
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=70"
        ]
        
        result = self.run_command(cmd)
        self.results["coverage_tests"] = result
        
        if result["success"]:
            self.log("覆盖率测试通过（≥70%）", "INFO")
        else:
            self.log("覆盖率测试失败（<70%）", "WARNING")
        
        return result["success"]
    
    def run_performance_tests(self) -> bool:
        """运行性能测试"""
        self.log("开始运行性能测试")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.tests_dir / "performance"),
            "-v",
            "--tb=short",
            "-m", "performance"
        ]
        
        result = self.run_command(cmd)
        self.results["performance_tests"] = result
        
        if result["success"]:
            self.log("性能测试通过", "INFO")
        else:
            self.log("性能测试失败", "WARNING")
        
        return result["success"]
    
    def check_environment(self) -> bool:
        """检查测试环境"""
        self.log("检查测试环境")
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 8):
            self.log(f"Python版本过低: {python_version}", "ERROR")
            return False
        
        # 检查必要的包
        required_packages = ["pytest", "httpx", "pytest-cov", "pytest-asyncio"]
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                self.log(f"缺少必要的包: {package}", "ERROR")
                return False
        
        # 检查配置
        try:
            self.log(f"当前环境: {settings.APP_ENV}")
            self.log(f"测试数据库: {settings.MONGODB_DB}")
        except Exception as e:
            self.log(f"配置检查失败: {e}", "ERROR")
            return False
        
        self.log("环境检查通过", "INFO")
        return True
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result["success"])
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "environment": settings.APP_ENV,
            "total_test_suites": total_tests,
            "passed_test_suites": passed_tests,
            "failed_test_suites": total_tests - passed_tests,
            "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%",
            "results": self.results
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_file: Optional[Path] = None):
        """保存测试报告"""
        if output_file is None:
            output_file = self.tests_dir / "logs" / "test_report.json"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"测试报告已保存: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RAG Chat 测试运行器")
    parser.add_argument("--type", choices=["unit", "integration", "comprehensive", "coverage", "performance", "all"], 
                       default="all", help="测试类型")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--output", "-o", type=Path, help="报告输出文件")
    parser.add_argument("--no-report", action="store_true", help="不生成报告")
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    # 检查环境
    if not runner.check_environment():
        sys.exit(1)
    
    # 运行测试
    success = True
    
    if args.type in ["unit", "all"]:
        success &= runner.run_unit_tests()
    
    if args.type in ["integration", "all"]:
        success &= runner.run_integration_tests()
    
    if args.type in ["comprehensive", "all"]:
        success &= runner.run_comprehensive_tests()
    
    if args.type in ["coverage", "all"]:
        success &= runner.run_coverage_tests()
    
    if args.type in ["performance", "all"]:
        success &= runner.run_performance_tests()
    
    # 生成报告
    if not args.no_report:
        report = runner.generate_report()
        runner.save_report(report, args.output)
        
        print("\n" + "="*50)
        print("测试总结")
        print("="*50)
        print(f"环境: {report['environment']}")
        print(f"测试套件: {report['passed_test_suites']}/{report['total_test_suites']} 通过")
        print(f"成功率: {report['success_rate']}")
        print("="*50)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
