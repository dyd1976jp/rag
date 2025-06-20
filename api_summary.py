#!/usr/bin/env python3
"""
RAG Chat API 端点摘要生成器
基于 API_DOCUMENTATION.md 生成简洁的API端点摘要
"""

import json
from typing import Dict, List

def generate_api_summary():
    """生成API端点摘要"""
    
    api_endpoints = {
        "认证模块": {
            "base_path": "/api/v1/auth",
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/register",
                    "description": "用户注册",
                    "auth_required": False,
                    "admin_required": False
                },
                {
                    "method": "POST", 
                    "path": "/login",
                    "description": "用户登录获取JWT令牌",
                    "auth_required": False,
                    "admin_required": False
                }
            ]
        },
        "大语言模型管理": {
            "base_path": "/api/v1/llm",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/",
                    "description": "获取所有LLM模型",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "GET",
                    "path": "/default", 
                    "description": "获取默认LLM模型",
                    "auth_required": False,
                    "admin_required": False
                },
                {
                    "method": "POST",
                    "path": "/",
                    "description": "创建LLM模型",
                    "auth_required": True,
                    "admin_required": True
                },
                {
                    "method": "PUT",
                    "path": "/{llm_id}",
                    "description": "更新LLM模型",
                    "auth_required": True,
                    "admin_required": True
                },
                {
                    "method": "DELETE",
                    "path": "/{llm_id}",
                    "description": "删除LLM模型",
                    "auth_required": True,
                    "admin_required": True
                },
                {
                    "method": "POST",
                    "path": "/test",
                    "description": "测试LLM模型",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "GET",
                    "path": "/discover-models",
                    "description": "发现本地模型",
                    "auth_required": True,
                    "admin_required": False
                }
            ]
        },
        "RAG检索增强生成": {
            "base_path": "/api/v1/rag",
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/documents/upload",
                    "description": "文档上传",
                    "auth_required": True,
                    "admin_required": False,
                    "content_type": "multipart/form-data"
                },
                {
                    "method": "POST",
                    "path": "/documents/search",
                    "description": "文档搜索",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "POST",
                    "path": "/chat",
                    "description": "RAG聊天",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "GET",
                    "path": "/documents",
                    "description": "获取文档列表",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "DELETE",
                    "path": "/documents/{document_id}",
                    "description": "删除文档",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "GET",
                    "path": "/status",
                    "description": "检查RAG服务状态",
                    "auth_required": True,
                    "admin_required": False
                }
            ]
        },
        "文档集合管理": {
            "base_path": "/api/v1/rag/collections",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/",
                    "description": "获取文档集列表",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "POST",
                    "path": "/",
                    "description": "创建文档集",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "GET",
                    "path": "/{collection_id}",
                    "description": "获取文档集详情",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "PUT",
                    "path": "/{collection_id}",
                    "description": "更新文档集",
                    "auth_required": True,
                    "admin_required": False
                },
                {
                    "method": "DELETE",
                    "path": "/{collection_id}",
                    "description": "删除文档集",
                    "auth_required": True,
                    "admin_required": False
                }
            ]
        },
        "管理模块": {
            "base_path": "/admin/api",
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/auth/login",
                    "description": "管理员登录",
                    "auth_required": False,
                    "admin_required": False
                },
                {
                    "method": "GET",
                    "path": "/mongodb/collections",
                    "description": "获取MongoDB集合",
                    "auth_required": True,
                    "admin_required": True
                },
                {
                    "method": "GET",
                    "path": "/vector/status",
                    "description": "获取向量存储状态",
                    "auth_required": True,
                    "admin_required": True
                },
                {
                    "method": "GET",
                    "path": "/system/status",
                    "description": "获取系统状态",
                    "auth_required": True,
                    "admin_required": True
                }
            ]
        }
    }
    
    return api_endpoints

def print_summary():
    """打印API摘要"""
    endpoints = generate_api_summary()
    
    print("=" * 60)
    print("RAG Chat API 端点摘要")
    print("=" * 60)
    print(f"基础URL: http://localhost:8000")
    print(f"认证方式: Bearer Token (JWT)")
    print()
    
    total_endpoints = 0
    auth_required_count = 0
    admin_required_count = 0
    
    for module_name, module_info in endpoints.items():
        print(f"📁 {module_name} ({module_info['base_path']})")
        print("-" * 50)
        
        for endpoint in module_info['endpoints']:
            total_endpoints += 1
            
            # 权限标识
            auth_icon = "🔒" if endpoint['auth_required'] else "🔓"
            admin_icon = "👑" if endpoint.get('admin_required', False) else ""
            
            if endpoint['auth_required']:
                auth_required_count += 1
            if endpoint.get('admin_required', False):
                admin_required_count += 1
            
            # 内容类型
            content_type = ""
            if endpoint.get('content_type'):
                content_type = f" ({endpoint['content_type']})"
            
            full_path = module_info['base_path'] + endpoint['path']
            print(f"  {auth_icon}{admin_icon} {endpoint['method']:6} {full_path:40} - {endpoint['description']}{content_type}")
        
        print()
    
    print("=" * 60)
    print("统计信息:")
    print(f"  总端点数: {total_endpoints}")
    print(f"  需要认证: {auth_required_count}")
    print(f"  需要管理员权限: {admin_required_count}")
    print(f"  公开端点: {total_endpoints - auth_required_count}")
    print()
    print("图例:")
    print("  🔓 - 公开端点（无需认证）")
    print("  🔒 - 需要用户认证")
    print("  👑 - 需要管理员权限")
    print("=" * 60)

def save_json_summary():
    """保存JSON格式的摘要"""
    endpoints = generate_api_summary()
    
    with open('api_endpoints_summary.json', 'w', encoding='utf-8') as f:
        json.dump(endpoints, f, ensure_ascii=False, indent=2)
    
    print("✅ API端点摘要已保存到 api_endpoints_summary.json")

if __name__ == "__main__":
    print_summary()
    save_json_summary()
