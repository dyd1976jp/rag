#!/usr/bin/env python3
"""
索引管理器演示脚本

这是一个简化的演示脚本，展示索引管理器的核心功能。
运行此脚本可以快速了解IndexProcessorFactory和ParentChildIndexProcessor的基本用法。
"""

import asyncio
import logging
from index_manager_usage import IndexManagerUsageExample

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_demo():
    """运行演示"""
    print("=" * 60)
    print("🚀 索引管理器演示")
    print("=" * 60)
    
    # 创建示例实例
    example = IndexManagerUsageExample()
    
    try:
        # 1. 初始化组件
        print("\n📦 初始化组件...")
        await example.setup_components()
        example.create_factory_and_processor()
        print("✅ 组件初始化完成")
        
        # 2. 基础使用演示
        print("\n🔧 基础使用演示...")
        basic_result = await example.basic_usage_example()
        print(f"✅ 基础使用完成: 处理了 {basic_result['extracted_documents']} 个文档")
        
        # 3. 配置示例演示
        print("\n⚙️  配置示例演示...")
        config_examples = example.configuration_examples()
        print(f"✅ 生成了 {len(config_examples)} 个配置示例")
        
        # 4. 实际场景演示
        print("\n🌟 实际场景演示...")
        scenario_result = await example.real_world_scenarios()
        print("✅ 实际场景演示完成:")
        print(f"   - PDF处理: {scenario_result['pdf_processing']['status']}")
        print(f"   - Markdown处理: {scenario_result['markdown_processing']['status']}")
        print(f"   - 批量处理: {scenario_result['batch_processing']['status']}")
        
        # 5. 性能测试演示
        print("\n⚡ 性能测试演示...")
        perf_result = await example.performance_and_testing_examples()
        avg_time = perf_result['retrieval_performance']['average_retrieval_time']
        print(f"✅ 性能测试完成: 平均检索时间 {avg_time:.3f}s")
        
        print("\n🎉 演示完成！")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {str(e)}")
        print(f"❌ 演示失败: {str(e)}")
    
    finally:
        # 清理资源
        await example.cleanup()
        print("🧹 资源清理完成")

def main():
    """主函数"""
    print("启动索引管理器演示...")
    asyncio.run(run_demo())

if __name__ == "__main__":
    main()
