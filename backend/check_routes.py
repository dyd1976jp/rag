#!/usr/bin/env python
"""
检查FastAPI应用程序中的所有路由
"""
import asyncio
from app.main import app

def print_routes():
    """打印所有路由"""
    print("应用程序中的所有路由:")
    print("-" * 40)
    
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", set())
            methods_str = ", ".join(methods) if methods else "N/A"
            endpoint = getattr(route, "endpoint", None)
            endpoint_name = endpoint.__name__ if endpoint else "N/A"
            print(f"路径: {route.path}")
            print(f"方法: {methods_str}")
            print(f"端点: {endpoint_name}")
            print(f"名称: {getattr(route, 'name', 'N/A')}")
            print("-" * 40)
    
    # 检查特定路由
    discover_routes = [route for route in app.routes if "discover" in str(route.path).lower()]
    if discover_routes:
        print("\n包含'discover'的路由:")
        for route in discover_routes:
            print(f"路径: {route.path}")
            print(f"方法: {getattr(route, 'methods', 'N/A')}")
            print(f"名称: {getattr(route, 'name', 'N/A')}")
            if hasattr(route, "endpoint"):
                print(f"端点函数: {route.endpoint.__name__}")
            print("-" * 40)
    else:
        print("\n没有找到包含'discover'的路由")

if __name__ == "__main__":
    print_routes() 