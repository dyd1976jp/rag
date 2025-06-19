#!/usr/bin/env python3
"""
简单测试文档清洗逻辑
"""

import re
import unicodedata

def old_clean_method(content):
    """旧的清洗方法（有问题的版本）"""
    # 规范化Unicode字符
    content = unicodedata.normalize('NFKC', content)
    
    # 替换多个连续空白字符为单个空格
    content = re.sub(r'\s+', ' ', content)
    
    # 删除控制字符
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    return content.strip()

def new_clean_method(content):
    """新的清洗方法（修复后的版本）"""
    # 规范化Unicode字符（使用NFC而不是NFKC，避免改变标点符号）
    content = unicodedata.normalize('NFC', content)
    
    # 删除控制字符，但保留换行符和制表符
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # 规范化空白字符，但保持换行符结构
    # 将多个连续空格替换为单个空格，但保留换行符
    content = re.sub(r'[ \t]+', ' ', content)  # 只处理空格和制表符
    
    # 清理多余的空行（超过2个连续换行符的情况）
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 清理行首行尾的空格
    lines = content.split('\n')
    lines = [line.strip() for line in lines]
    content = '\n'.join(lines)
    
    return content.strip()

def test_cleaning():
    """测试清洗功能"""
    test_content = """第一章：引言

这是第一章的内容。
它包含多行文本。

第二章：方法

这是第二章的内容。
包含了详细的方法描述。

第三章：结果

实验结果如下：
1. 结果一
2. 结果二
3. 结果三

第四章：总结

总结内容在这里。"""

    print("=== 原始内容 ===")
    print(repr(test_content))
    print(f"长度: {len(test_content)}")
    print(f"换行符数量: {test_content.count(chr(10))}")
    print(f"包含中文冒号: {'：' in test_content}")
    
    print("\n=== 旧方法清洗结果 ===")
    old_result = old_clean_method(test_content)
    print(repr(old_result))
    print(f"长度: {len(old_result)}")
    print(f"换行符数量: {old_result.count(chr(10))}")
    print(f"包含中文冒号: {'：' in old_result}")
    print(f"包含半角冒号: {':' in old_result}")
    
    print("\n=== 新方法清洗结果 ===")
    new_result = new_clean_method(test_content)
    print(repr(new_result))
    print(f"长度: {len(new_result)}")
    print(f"换行符数量: {new_result.count(chr(10))}")
    print(f"包含中文冒号: {'：' in new_result}")
    print(f"包含半角冒号: {':' in new_result}")
    
    print("\n=== 对比分析 ===")
    if old_result.count('\n') == 0:
        print("✗ 旧方法：所有换行符被移除")
    else:
        print("✓ 旧方法：保留了换行符")
        
    if new_result.count('\n') > 0:
        print("✓ 新方法：保留了换行符")
    else:
        print("✗ 新方法：换行符被移除")
    
    if '：' in old_result:
        print("✓ 旧方法：保留了中文冒号")
    else:
        print("✗ 旧方法：中文冒号被改变")
        
    if '：' in new_result:
        print("✓ 新方法：保留了中文冒号")
    else:
        print("✗ 新方法：中文冒号被改变")

def test_splitting_simulation():
    """模拟分割测试"""
    test_content = """第一章：引言

这是第一章的内容。
它包含多行文本。

第二章：方法

这是第二章的内容。
包含了详细的方法描述。"""

    print("\n=== 分割模拟测试 ===")
    
    # 使用新方法清洗
    cleaned = new_clean_method(test_content)
    
    # 模拟按 \n\n 分割
    parent_separator = "\n\n"
    parent_chunks = cleaned.split(parent_separator)
    parent_chunks = [chunk.strip() for chunk in parent_chunks if chunk.strip()]
    
    print(f"按 '{parent_separator}' 分割得到 {len(parent_chunks)} 个父块:")
    for i, chunk in enumerate(parent_chunks):
        print(f"父块 {i+1}: {repr(chunk[:50])}")
        
        # 模拟按 \n 分割子块
        child_separator = "\n"
        child_chunks = chunk.split(child_separator)
        child_chunks = [child.strip() for child in child_chunks if child.strip()]
        
        print(f"  -> 子块数量: {len(child_chunks)}")
        for j, child in enumerate(child_chunks):
            print(f"     子块 {j+1}: {repr(child[:30])}")

if __name__ == "__main__":
    print("开始测试文档清洗修复...")
    test_cleaning()
    test_splitting_simulation()
    print("\n测试完成！")
