#!/usr/bin/env python3
"""
API性能基准测试

测试不同负载下的API性能表现
"""

import requests
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE_URL = "http://localhost:8000/api/v1"
ENDPOINT = f"{API_BASE_URL}/rag/documents/preview-split"

def single_request(content_size="medium"):
    """单个请求测试"""
    content_map = {
        "small": "这是小文本。\n\n测试内容。",
        "medium": "这是中等长度的测试文本。" * 20 + "\n\n" + "第二段内容。" * 20,
        "large": "这是大文本测试。" * 200 + "\n\n" + "第二段大内容。" * 200
    }
    
    test_data = {
        "content": content_map.get(content_size, content_map["medium"]),
        "parent_chunk_size": 200,
        "child_chunk_size": 100
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            ENDPOINT,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response_time = time.time() - start_time
        return {
            "success": response.status_code in [200, 401],
            "status_code": response.status_code,
            "response_time": response_time,
            "content_size": len(test_data["content"])
        }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            "success": False,
            "status_code": None,
            "response_time": response_time,
            "error": str(e),
            "content_size": len(test_data["content"])
        }

def benchmark_content_sizes():
    """测试不同内容大小的性能"""
    print("=" * 60)
    print("内容大小性能基准测试")
    print("=" * 60)
    
    sizes = ["small", "medium", "large"]
    
    for size in sizes:
        print(f"\n测试 {size} 内容:")
        
        # 执行5次测试
        results = []
        for i in range(5):
            result = single_request(size)
            results.append(result)
            status = "✅" if result["success"] else "❌"
            print(f"  请求 {i+1}: {status} {result['response_time']:.3f}s (HTTP {result.get('status_code', 'N/A')})")
        
        # 统计结果
        successful_results = [r for r in results if r["success"]]
        if successful_results:
            response_times = [r["response_time"] for r in successful_results]
            content_size = successful_results[0]["content_size"]
            
            print(f"  内容大小: {content_size:,} 字符")
            print(f"  成功率: {len(successful_results)}/{len(results)} ({len(successful_results)/len(results):.1%})")
            print(f"  平均响应时间: {statistics.mean(response_times):.3f}s")
            print(f"  最大响应时间: {max(response_times):.3f}s")
            print(f"  最小响应时间: {min(response_times):.3f}s")
            if len(response_times) > 1:
                print(f"  标准差: {statistics.stdev(response_times):.3f}s")

def benchmark_concurrent_load():
    """测试并发负载性能"""
    print("\n" + "=" * 60)
    print("并发负载性能基准测试")
    print("=" * 60)
    
    concurrent_levels = [1, 3, 5, 10]
    
    for concurrent_count in concurrent_levels:
        print(f"\n测试 {concurrent_count} 个并发请求:")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            # 提交所有请求
            futures = [executor.submit(single_request, "medium") for _ in range(concurrent_count)]
            
            # 收集结果
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_results = [r for r in results if r["success"]]
        
        print(f"  总耗时: {total_time:.3f}s")
        print(f"  成功率: {len(successful_results)}/{len(results)} ({len(successful_results)/len(results):.1%})")
        
        if successful_results:
            response_times = [r["response_time"] for r in successful_results]
            print(f"  平均响应时间: {statistics.mean(response_times):.3f}s")
            print(f"  最大响应时间: {max(response_times):.3f}s")
            print(f"  最小响应时间: {min(response_times):.3f}s")
            print(f"  吞吐量: {len(successful_results)/total_time:.2f} 请求/秒")

def benchmark_sustained_load():
    """测试持续负载性能"""
    print("\n" + "=" * 60)
    print("持续负载性能基准测试")
    print("=" * 60)
    
    duration = 30  # 30秒测试
    print(f"执行 {duration} 秒持续负载测试...")
    
    results = []
    start_time = time.time()
    request_count = 0
    
    while time.time() - start_time < duration:
        result = single_request("medium")
        results.append(result)
        request_count += 1
        
        if request_count % 10 == 0:
            elapsed = time.time() - start_time
            print(f"  已执行 {request_count} 个请求，耗时 {elapsed:.1f}s")
        
        # 短暂休息避免过度负载
        time.sleep(0.1)
    
    total_time = time.time() - start_time
    successful_results = [r for r in results if r["success"]]
    
    print(f"\n持续负载测试结果:")
    print(f"  测试时长: {total_time:.1f}s")
    print(f"  总请求数: {len(results)}")
    print(f"  成功请求数: {len(successful_results)}")
    print(f"  成功率: {len(successful_results)/len(results):.1%}")
    print(f"  平均吞吐量: {len(successful_results)/total_time:.2f} 请求/秒")
    
    if successful_results:
        response_times = [r["response_time"] for r in successful_results]
        print(f"  平均响应时间: {statistics.mean(response_times):.3f}s")
        print(f"  95%分位响应时间: {sorted(response_times)[int(len(response_times)*0.95)]:.3f}s")
        print(f"  99%分位响应时间: {sorted(response_times)[int(len(response_times)*0.99)]:.3f}s")

def check_server_health():
    """检查服务器健康状态"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器健康检查通过")
            return True
        else:
            print(f"❌ 服务器健康检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 服务器连接失败: {e}")
        return False

def main():
    print("🚀 API性能基准测试开始")
    print("=" * 80)
    
    # 健康检查
    if not check_server_health():
        print("服务器不可用，终止测试")
        return
    
    # 执行各项基准测试
    benchmark_content_sizes()
    benchmark_concurrent_load()
    benchmark_sustained_load()
    
    print("\n" + "=" * 80)
    print("🎉 性能基准测试完成")
    print("=" * 80)
    
    print("\n性能评估标准:")
    print("  优秀: 平均响应时间 < 0.1s, 并发成功率 > 95%")
    print("  良好: 平均响应时间 < 0.5s, 并发成功率 > 90%")
    print("  可接受: 平均响应时间 < 2.0s, 并发成功率 > 80%")

if __name__ == "__main__":
    main()
