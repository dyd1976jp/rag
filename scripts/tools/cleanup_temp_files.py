#!/usr/bin/env python3
"""
临时文件清理脚本

根据PLANNING.md中定义的文件管理规范，清理过时的临时文件。
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime, timedelta
import argparse


class TempFilesCleaner:
    """临时文件清理器"""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.cleaned_files = []
        self.cleaned_dirs = []
        self.errors = []
        
    def clean_temp_directory(self, max_age_days: int = 30) -> None:
        """清理temp目录中的过时文件"""
        print(f"🔍 清理temp目录中超过{max_age_days}天的文件...")
        
        temp_dir = self.project_root / "temp"
        if not temp_dir.exists():
            print("   temp目录不存在，跳过")
            return
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for item in temp_dir.rglob("*"):
            if item.is_file():
                try:
                    # 获取文件修改时间
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    
                    if mtime < cutoff_date:
                        if self.dry_run:
                            print(f"   [DRY RUN] 将删除文件: {item.relative_to(self.project_root)}")
                            self.cleaned_files.append(str(item.relative_to(self.project_root)))
                        else:
                            print(f"   删除文件: {item.relative_to(self.project_root)}")
                            item.unlink()
                            self.cleaned_files.append(str(item.relative_to(self.project_root)))
                            
                except Exception as e:
                    self.errors.append(f"删除文件失败 {item}: {e}")
    
    def clean_cache_directories(self, max_age_days: int = 7) -> None:
        """清理缓存目录"""
        print(f"🔍 清理缓存目录中超过{max_age_days}天的文件...")
        
        cache_dirs = [
            self.project_root / "data" / "cache",
            self.project_root / "data" / "splitter_cache",
            self.project_root / "backend" / "__pycache__",
        ]
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
                
            print(f"   处理缓存目录: {cache_dir.relative_to(self.project_root)}")
            
            for item in cache_dir.rglob("*"):
                if item.is_file():
                    try:
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        
                        if mtime < cutoff_date:
                            if self.dry_run:
                                print(f"   [DRY RUN] 将删除缓存文件: {item.relative_to(self.project_root)}")
                                self.cleaned_files.append(str(item.relative_to(self.project_root)))
                            else:
                                print(f"   删除缓存文件: {item.relative_to(self.project_root)}")
                                item.unlink()
                                self.cleaned_files.append(str(item.relative_to(self.project_root)))
                                
                    except Exception as e:
                        self.errors.append(f"删除缓存文件失败 {item}: {e}")
    
    def clean_log_files(self, max_age_days: int = 30) -> None:
        """清理旧的日志文件"""
        print(f"🔍 清理超过{max_age_days}天的日志文件...")
        
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            print("   logs目录不存在，跳过")
            return
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for log_file in logs_dir.rglob("*.log*"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if mtime < cutoff_date:
                    if self.dry_run:
                        print(f"   [DRY RUN] 将删除日志文件: {log_file.relative_to(self.project_root)}")
                        self.cleaned_files.append(str(log_file.relative_to(self.project_root)))
                    else:
                        print(f"   删除日志文件: {log_file.relative_to(self.project_root)}")
                        log_file.unlink()
                        self.cleaned_files.append(str(log_file.relative_to(self.project_root)))
                        
            except Exception as e:
                self.errors.append(f"删除日志文件失败 {log_file}: {e}")
    
    def clean_backup_files(self, max_age_days: int = 90) -> None:
        """清理旧的备份文件"""
        print(f"🔍 清理超过{max_age_days}天的备份文件...")
        
        # 查找备份目录和文件
        backup_patterns = [
            "*backup*",
            "*-backup-*",
            "*.bak",
            "*~"
        ]
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for pattern in backup_patterns:
            for item in self.project_root.rglob(pattern):
                if item.is_file() or item.is_dir():
                    try:
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        
                        if mtime < cutoff_date:
                            if self.dry_run:
                                if item.is_dir():
                                    print(f"   [DRY RUN] 将删除备份目录: {item.relative_to(self.project_root)}")
                                    self.cleaned_dirs.append(str(item.relative_to(self.project_root)))
                                else:
                                    print(f"   [DRY RUN] 将删除备份文件: {item.relative_to(self.project_root)}")
                                    self.cleaned_files.append(str(item.relative_to(self.project_root)))
                            else:
                                if item.is_dir():
                                    print(f"   删除备份目录: {item.relative_to(self.project_root)}")
                                    shutil.rmtree(item)
                                    self.cleaned_dirs.append(str(item.relative_to(self.project_root)))
                                else:
                                    print(f"   删除备份文件: {item.relative_to(self.project_root)}")
                                    item.unlink()
                                    self.cleaned_files.append(str(item.relative_to(self.project_root)))
                                    
                    except Exception as e:
                        self.errors.append(f"删除备份项失败 {item}: {e}")
    
    def clean_empty_directories(self) -> None:
        """清理空目录"""
        print("🔍 清理空目录...")
        
        # 从深层目录开始，向上清理空目录
        all_dirs = list(self.project_root.rglob("*"))
        all_dirs = [d for d in all_dirs if d.is_dir()]
        all_dirs.sort(key=lambda x: len(x.parts), reverse=True)
        
        for dir_path in all_dirs:
            # 跳过重要目录
            if dir_path.name in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']:
                continue
            
            try:
                # 检查目录是否为空
                if dir_path.exists() and not any(dir_path.iterdir()):
                    # 不删除重要的空目录
                    important_dirs = ['logs', 'temp', 'data', 'cache']
                    if any(important in str(dir_path) for important in important_dirs):
                        continue
                    
                    if self.dry_run:
                        print(f"   [DRY RUN] 将删除空目录: {dir_path.relative_to(self.project_root)}")
                        self.cleaned_dirs.append(str(dir_path.relative_to(self.project_root)))
                    else:
                        print(f"   删除空目录: {dir_path.relative_to(self.project_root)}")
                        dir_path.rmdir()
                        self.cleaned_dirs.append(str(dir_path.relative_to(self.project_root)))
                        
            except Exception as e:
                self.errors.append(f"删除空目录失败 {dir_path}: {e}")
    
    def generate_report(self) -> Dict:
        """生成清理报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "dry_run": self.dry_run,
            "cleaned_files": self.cleaned_files,
            "cleaned_directories": self.cleaned_dirs,
            "errors": self.errors,
            "total_cleaned_files": len(self.cleaned_files),
            "total_cleaned_directories": len(self.cleaned_dirs),
            "total_errors": len(self.errors)
        }
    
    def run_cleanup(self, temp_days: int = 30, cache_days: int = 7, 
                   log_days: int = 30, backup_days: int = 90) -> Dict:
        """运行完整清理"""
        mode_str = "DRY RUN" if self.dry_run else "ACTUAL"
        print(f"🚀 开始临时文件清理 ({mode_str})...")
        print(f"📁 项目根目录: {self.project_root}")
        print()
        
        # 执行各项清理
        self.clean_temp_directory(temp_days)
        self.clean_cache_directories(cache_days)
        self.clean_log_files(log_days)
        self.clean_backup_files(backup_days)
        self.clean_empty_directories()
        
        # 生成报告
        report = self.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("📊 清理结果摘要")
        print("="*60)
        
        if self.dry_run:
            print("🔍 DRY RUN 模式 - 未实际删除文件")
        
        print(f"📄 清理的文件数: {report['total_cleaned_files']}")
        print(f"📁 清理的目录数: {report['total_cleaned_directories']}")
        
        if report['total_errors'] > 0:
            print(f"❌ 错误数: {report['total_errors']}")
            for error in self.errors:
                print(f"   {error}")
        
        # 保存报告
        report_file = self.project_root / "temp" / "cleanup_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="清理项目中的临时文件")
    parser.add_argument("--project-root", default=None, help="项目根目录路径")
    parser.add_argument("--dry-run", action="store_true", default=True, help="仅显示将要删除的文件，不实际删除")
    parser.add_argument("--execute", action="store_true", help="实际执行删除操作")
    parser.add_argument("--temp-days", type=int, default=30, help="temp目录文件保留天数")
    parser.add_argument("--cache-days", type=int, default=7, help="缓存文件保留天数")
    parser.add_argument("--log-days", type=int, default=30, help="日志文件保留天数")
    parser.add_argument("--backup-days", type=int, default=90, help="备份文件保留天数")
    
    args = parser.parse_args()
    
    # 获取项目根目录
    if args.project_root:
        project_root = args.project_root
    else:
        # 假设脚本在 scripts/tools/ 目录中
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
    
    # 确定是否为dry run模式
    dry_run = not args.execute
    
    # 运行清理
    cleaner = TempFilesCleaner(project_root, dry_run=dry_run)
    report = cleaner.run_cleanup(
        temp_days=args.temp_days,
        cache_days=args.cache_days,
        log_days=args.log_days,
        backup_days=args.backup_days
    )
    
    # 设置退出码
    sys.exit(0 if report['total_errors'] == 0 else 1)


if __name__ == "__main__":
    main()
