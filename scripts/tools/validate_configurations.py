#!/usr/bin/env python3
"""
配置文件验证脚本

验证项目中各种配置文件的一致性和完整性，包括：
- 环境变量配置文件
- Docker配置文件
- Python项目配置
- 前端项目配置
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import toml
    HAS_TOML = True
except ImportError:
    HAS_TOML = False


class ConfigurationValidator:
    """配置验证器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.warnings = []
        self.recommendations = []
        
    def validate_env_files(self) -> None:
        """验证环境变量配置文件"""
        print("🔍 验证环境变量配置文件...")
        
        env_files = [
            ".env.example",
            ".env.development", 
            ".env.production",
            ".env.test"
        ]
        
        env_configs = {}
        
        # 读取所有环境配置文件
        for env_file in env_files:
            file_path = self.project_root / env_file
            if file_path.exists():
                try:
                    config = self._parse_env_file(file_path)
                    env_configs[env_file] = config
                    print(f"   ✅ {env_file}: {len(config)} 个配置项")
                except Exception as e:
                    self.issues.append(f"无法解析 {env_file}: {e}")
            else:
                self.warnings.append(f"环境配置文件不存在: {env_file}")
        
        # 检查配置一致性
        if len(env_configs) > 1:
            self._check_env_consistency(env_configs)
    
    def _parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """解析环境变量文件"""
        config = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        return config
    
    def _check_env_consistency(self, env_configs: Dict[str, Dict[str, str]]) -> None:
        """检查环境配置一致性"""
        print("   🔍 检查环境配置一致性...")
        
        # 获取所有配置键
        all_keys = set()
        for config in env_configs.values():
            all_keys.update(config.keys())
        
        # 检查每个配置文件是否包含所有必要的键
        example_keys = set(env_configs.get('.env.example', {}).keys())
        
        for env_file, config in env_configs.items():
            if env_file == '.env.example':
                continue
                
            config_keys = set(config.keys())
            
            # 检查缺失的键
            missing_keys = example_keys - config_keys
            if missing_keys:
                self.warnings.append(f"{env_file} 缺少配置项: {', '.join(missing_keys)}")
            
            # 检查多余的键
            extra_keys = config_keys - example_keys
            if extra_keys:
                self.warnings.append(f"{env_file} 包含额外配置项: {', '.join(extra_keys)}")
    
    def validate_docker_configs(self) -> None:
        """验证Docker配置文件"""
        print("🔍 验证Docker配置文件...")

        docker_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.prod.yml"
        ]

        for docker_file in docker_files:
            file_path = self.project_root / docker_file
            if file_path.exists():
                try:
                    if docker_file.startswith("docker-compose"):
                        if HAS_YAML:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                config = yaml.safe_load(f)
                            self._validate_docker_compose(docker_file, config)
                        else:
                            print(f"   ⚠️  {docker_file}: 跳过验证（缺少yaml模块）")
                    else:
                        # 简单检查Dockerfile语法
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        self._validate_dockerfile(docker_file, content)

                    print(f"   ✅ {docker_file}: 格式正确")
                except Exception as e:
                    self.issues.append(f"Docker配置文件错误 {docker_file}: {e}")
            else:
                self.warnings.append(f"Docker配置文件不存在: {docker_file}")
    
    def _validate_docker_compose(self, filename: str, config: Dict) -> None:
        """验证docker-compose配置"""
        required_sections = ['services']
        
        for section in required_sections:
            if section not in config:
                self.issues.append(f"{filename} 缺少必需部分: {section}")
        
        # 检查服务配置
        if 'services' in config:
            services = config['services']
            for service_name, service_config in services.items():
                if 'image' not in service_config and 'build' not in service_config:
                    self.warnings.append(f"{filename} 服务 {service_name} 缺少image或build配置")
    
    def _validate_dockerfile(self, filename: str, content: str) -> None:
        """验证Dockerfile内容"""
        lines = content.split('\n')
        
        # 检查是否有FROM指令
        has_from = any(line.strip().upper().startswith('FROM') for line in lines)
        if not has_from:
            self.issues.append(f"{filename} 缺少FROM指令")
        
        # 检查常见的最佳实践
        if 'apt-get update' in content and 'apt-get clean' not in content:
            self.warnings.append(f"{filename} 建议在apt-get update后添加清理命令")
    
    def validate_python_config(self) -> None:
        """验证Python项目配置"""
        print("🔍 验证Python项目配置...")
        
        # 检查pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            if HAS_TOML:
                try:
                    with open(pyproject_path, 'r', encoding='utf-8') as f:
                        config = toml.load(f)
                    self._validate_pyproject(config)
                    print(f"   ✅ pyproject.toml: 配置正确")
                except Exception as e:
                    self.issues.append(f"pyproject.toml 解析错误: {e}")
            else:
                print(f"   ⚠️  pyproject.toml: 跳过验证（缺少toml模块）")
        else:
            self.warnings.append("pyproject.toml 文件不存在")
        
        # 检查requirements文件
        req_files = ["requirements.txt", "backend/requirements.txt", "backend/requirements-dev.txt"]
        for req_file in req_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._validate_requirements(req_file, content)
                    print(f"   ✅ {req_file}: 格式正确")
                except Exception as e:
                    self.issues.append(f"requirements文件错误 {req_file}: {e}")
    
    def _validate_pyproject(self, config: Dict) -> None:
        """验证pyproject.toml配置"""
        required_sections = ['project', 'build-system']
        
        for section in required_sections:
            if section not in config:
                self.issues.append(f"pyproject.toml 缺少必需部分: {section}")
        
        # 检查项目信息
        if 'project' in config:
            project = config['project']
            required_fields = ['name', 'version', 'description']
            for field in required_fields:
                if field not in project:
                    self.warnings.append(f"pyproject.toml project部分缺少字段: {field}")
    
    def _validate_requirements(self, filename: str, content: str) -> None:
        """验证requirements文件"""
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # 简单检查包名格式
                if not any(char in line for char in ['==', '>=', '<=', '>', '<', '~=']):
                    self.warnings.append(f"{filename}:{line_num} 建议指定版本: {line}")
    
    def validate_frontend_config(self) -> None:
        """验证前端项目配置"""
        print("🔍 验证前端项目配置...")
        
        frontend_dir = self.project_root / "frontend-app"
        if not frontend_dir.exists():
            self.warnings.append("前端项目目录不存在")
            return
        
        # 检查package.json
        package_json_path = frontend_dir / "package.json"
        if package_json_path.exists():
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._validate_package_json(config)
                print(f"   ✅ package.json: 配置正确")
            except Exception as e:
                self.issues.append(f"package.json 解析错误: {e}")
        else:
            self.issues.append("package.json 文件不存在")
        
        # 检查TypeScript配置
        ts_config_path = frontend_dir / "tsconfig.json"
        if ts_config_path.exists():
            try:
                with open(ts_config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # TypeScript配置文件支持注释，简单检查格式
                if '"compilerOptions"' in content and '"include"' in content:
                    print(f"   ✅ tsconfig.json: 配置正确")
                else:
                    self.warnings.append("tsconfig.json 缺少必要的配置部分")
            except Exception as e:
                self.issues.append(f"tsconfig.json 读取错误: {e}")
    
    def _validate_package_json(self, config: Dict) -> None:
        """验证package.json配置"""
        required_fields = ['name', 'version', 'scripts']
        
        for field in required_fields:
            if field not in config:
                self.issues.append(f"package.json 缺少必需字段: {field}")
        
        # 检查脚本配置
        if 'scripts' in config:
            scripts = config['scripts']
            recommended_scripts = ['dev', 'build', 'preview']
            for script in recommended_scripts:
                if script not in scripts:
                    self.warnings.append(f"package.json 建议添加脚本: {script}")
    
    def generate_recommendations(self) -> None:
        """生成配置优化建议"""
        print("🔍 生成配置优化建议...")
        
        # 基于发现的问题生成建议
        if self.issues:
            self.recommendations.append({
                "type": "critical",
                "title": "修复配置错误",
                "description": f"发现{len(self.issues)}个配置错误需要立即修复",
                "action": "检查并修复所有配置文件错误"
            })
        
        if self.warnings:
            self.recommendations.append({
                "type": "improvement",
                "title": "优化配置设置",
                "description": f"发现{len(self.warnings)}个配置改进建议",
                "action": "根据警告信息优化配置文件"
            })
        
        # 添加通用建议
        self.recommendations.extend([
            {
                "type": "security",
                "title": "配置安全检查",
                "description": "定期检查配置文件中的敏感信息",
                "action": "确保生产环境配置不包含测试数据或默认密码"
            },
            {
                "type": "maintenance",
                "title": "配置版本管理",
                "description": "建立配置文件版本管理机制",
                "action": "使用Git跟踪配置变更，建立配置审核流程"
            }
        ])
    
    def generate_report(self) -> Dict:
        """生成验证报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "summary": {
                "total_issues": len(self.issues),
                "total_warnings": len(self.warnings),
                "total_recommendations": len(self.recommendations),
                "is_valid": len(self.issues) == 0
            }
        }
    
    def run_validation(self) -> Dict:
        """运行完整验证"""
        print("🚀 开始配置文件验证...")
        print(f"📁 项目根目录: {self.project_root}")
        print()
        
        # 运行各项验证
        self.validate_env_files()
        self.validate_docker_configs()
        self.validate_python_config()
        self.validate_frontend_config()
        self.generate_recommendations()
        
        # 生成报告
        report = self.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("📊 配置验证结果摘要")
        print("="*60)
        
        summary = report["summary"]
        if summary["is_valid"]:
            print("✅ 所有配置文件验证通过！")
        else:
            print(f"❌ 发现 {summary['total_issues']} 个配置错误")
        
        if summary["total_warnings"] > 0:
            print(f"⚠️  发现 {summary['total_warnings']} 个配置警告")
        
        print(f"💡 生成 {summary['total_recommendations']} 条优化建议")
        
        # 显示主要问题
        if self.issues:
            print("\n🚨 配置错误:")
            for i, issue in enumerate(self.issues[:5], 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print("\n⚠️  配置警告:")
            for i, warning in enumerate(self.warnings[:5], 1):
                print(f"  {i}. {warning}")
        
        # 保存报告
        report_file = self.project_root / "temp" / "configuration_validation_report.json"
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
    
    # 运行验证
    validator = ConfigurationValidator(project_root)
    report = validator.run_validation()
    
    # 设置退出码
    sys.exit(0 if report["summary"]["is_valid"] else 1)


if __name__ == "__main__":
    main()
