#!/usr/bin/env python
"""
测试FastAPI应用程序中的所有路由
"""
import pytest
from app.main import app

def test_print_routes():
    """测试打印所有路由"""
    # 检查是否有路由
    assert len(app.routes) > 0, "应用程序应该至少有一个路由"
    
    routes_info = []
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", set())
            methods_str = ", ".join(methods) if methods else "N/A"
            endpoint = getattr(route, "endpoint", None)
            endpoint_name = endpoint.__name__ if endpoint else "N/A"
            route_info = {
                "path": route.path,
                "methods": methods_str,
                "endpoint": endpoint_name,
                "name": getattr(route, "name", "N/A")
            }
            routes_info.append(route_info)
    
    # 验证路由信息是否正确
    assert all(isinstance(route["path"], str) for route in routes_info), "所有路由路径应该是字符串"
    assert all(isinstance(route["methods"], str) for route in routes_info), "所有路由方法应该是字符串"

def test_discover_routes():
    """测试查找特定路由"""
    # 检查discover相关路由
    discover_routes = [route for route in app.routes if "discover" in str(route.path).lower()]
    
    # 记录找到的discover路由信息
    discover_routes_info = []
    for route in discover_routes:
        route_info = {
            "path": route.path,
            "methods": getattr(route, "methods", "N/A"),
            "name": getattr(route, "name", "N/A"),
            "endpoint": route.endpoint.__name__ if hasattr(route, "endpoint") else "N/A"
        }
        discover_routes_info.append(route_info)
    
    # 可以根据实际需求添加具体的断言
    # 例如：验证是否存在特定的discover路由
    # assert any("discover" in route["path"] for route in discover_routes_info), "应该至少有一个discover路由" 