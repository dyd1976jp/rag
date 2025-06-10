#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接测试discover_local_models函数，绕过API路由
"""

import asyncio
import json
from app.services.llm_service import llm_service  # 导入服务

async def test_discover_direct():
    """直接测试discover_local_models函数"""
    print("\n=== 直接测试discover_local_models函数 ===")
    
    # LM Studio URL
    lm_studio_url = "http://0.0.0.0:1234"
    
    try:
        print(f"调用discover_local_models: provider=lmstudio, url={lm_studio_url}")
        
        # 直接调用服务函数
        result = await llm_service.discover_local_models("lmstudio", lm_studio_url)
        
        print(f"调用结果类型: {type(result)}")
        print(f"结果长度: {len(result) if result else 0}")
        
        if result:
            if "error" in result[0]:
                print(f"发现错误: {result[0].get('error')}")
                if "details" in result[0]:
                    print(f"错误详情: {result[0].get('details')}")
            else:
                print("发现的模型:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("未发现任何模型")
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")

if __name__ == "__main__":
    # 运行异步函数
    asyncio.run(test_discover_direct()) 