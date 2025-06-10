#!/usr/bin/env python
"""
直接测试LLM服务的脚本
"""

import asyncio
from app.services.llm_service import llm_service

async def test_discover_local_models():
    """测试discover_local_models函数"""
    print("\n===== 测试discover_local_models函数 =====")
    
    provider = "lmstudio"
    url = "http://localhost:1234"
    
    print(f"调用参数: provider={provider}, url={url}")
    result = await llm_service.discover_local_models(provider, url)
    
    print(f"返回结果类型: {type(result)}")
    print(f"返回结果长度: {len(result) if result else 0}")
    print(f"返回结果: {result}")
    
    return result

async def main():
    """主函数"""
    try:
        await test_discover_local_models()
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 