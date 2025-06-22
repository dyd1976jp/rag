#!/usr/bin/env python3
"""
API文档生成脚本

自动生成API文档，包括端点列表、参数说明和响应格式。
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import importlib.util

# 添加backend目录到Python路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from app.main import app
    from fastapi.openapi.utils import get_openapi
except ImportError as e:
    print(f"无法导入FastAPI应用: {e}")
    print("请确保在backend目录中运行此脚本，并且已安装所有依赖")
    sys.exit(1)


def generate_openapi_spec() -> Dict[str, Any]:
    """
    生成OpenAPI规范
    
    Returns:
        Dict: OpenAPI规范字典
    """
    return get_openapi(
        title="RAG Chat API",
        version="1.0.0",
        description="RAG Chat系统的RESTful API文档",
        routes=app.routes,
    )


def format_endpoint_docs(openapi_spec: Dict[str, Any]) -> str:
    """
    格式化端点文档
    
    Args:
        openapi_spec: OpenAPI规范
        
    Returns:
        str: 格式化的Markdown文档
    """
    docs = []
    docs.append("# RAG Chat API 文档\n")
    docs.append("## 概述\n")
    docs.append("RAG Chat系统提供了完整的文档检索增强生成(RAG)功能，包括文档上传、处理、搜索和聊天等功能。\n")
    
    docs.append("## 基础信息\n")
    docs.append("- **基础URL**: `http://localhost:8000`")
    docs.append("- **API版本**: v1")
    docs.append("- **认证方式**: Bearer Token\n")
    
    docs.append("## 端点列表\n")
    
    # 按标签分组端点
    endpoints_by_tag: Dict[str, List] = {}
    
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                tags = details.get("tags", ["未分类"])
                tag = tags[0] if tags else "未分类"
                
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                
                endpoints_by_tag[tag].append({
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": details.get("parameters", []),
                    "requestBody": details.get("requestBody", {}),
                    "responses": details.get("responses", {})
                })
    
    # 生成每个标签的文档
    for tag, endpoints in endpoints_by_tag.items():
        docs.append(f"### {tag}\n")
        
        for endpoint in endpoints:
            docs.append(f"#### {endpoint['method']} {endpoint['path']}\n")
            
            if endpoint['summary']:
                docs.append(f"**摘要**: {endpoint['summary']}\n")
            
            if endpoint['description']:
                docs.append(f"**描述**: {endpoint['description']}\n")
            
            # 参数文档
            if endpoint['parameters']:
                docs.append("**参数**:\n")
                for param in endpoint['parameters']:
                    param_name = param.get('name', '')
                    param_type = param.get('schema', {}).get('type', 'string')
                    param_desc = param.get('description', '')
                    param_required = '必需' if param.get('required', False) else '可选'
                    docs.append(f"- `{param_name}` ({param_type}, {param_required}): {param_desc}")
                docs.append("")
            
            # 请求体文档
            if endpoint['requestBody']:
                docs.append("**请求体**:\n")
                content = endpoint['requestBody'].get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    docs.append(f"```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```\n")
            
            # 响应文档
            if endpoint['responses']:
                docs.append("**响应**:\n")
                for status_code, response in endpoint['responses'].items():
                    desc = response.get('description', '')
                    docs.append(f"- **{status_code}**: {desc}")
                docs.append("")
            
            docs.append("---\n")
    
    return "\n".join(docs)


def save_docs(content: str, output_path: str) -> None:
    """
    保存文档到文件
    
    Args:
        content: 文档内容
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"API文档已生成: {output_path}")


def main() -> None:
    """主函数"""
    try:
        # 生成OpenAPI规范
        print("正在生成OpenAPI规范...")
        openapi_spec = generate_openapi_spec()
        
        # 保存OpenAPI JSON文件
        openapi_path = backend_path / "docs" / "openapi.json"
        openapi_path.parent.mkdir(exist_ok=True)
        
        with open(openapi_path, 'w', encoding='utf-8') as f:
            json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        print(f"OpenAPI规范已保存: {openapi_path}")
        
        # 生成Markdown文档
        print("正在生成Markdown文档...")
        markdown_content = format_endpoint_docs(openapi_spec)
        
        # 保存Markdown文件
        docs_path = backend_path.parent / "docs" / "API.md"
        docs_path.parent.mkdir(exist_ok=True)
        save_docs(markdown_content, str(docs_path))
        
        print("✅ API文档生成完成！")
        print(f"📄 Markdown文档: {docs_path}")
        print(f"📋 OpenAPI规范: {openapi_path}")
        
    except Exception as e:
        print(f"❌ 生成API文档时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
