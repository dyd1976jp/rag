#!/usr/bin/env python3
"""
简单测试分割逻辑
"""

def test_split_logic():
    """测试分割逻辑"""
    
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
    print(f"长度: {len(test_content)}")
    print(f"\\n\\n 数量: {test_content.count(chr(10)+chr(10))}")
    
    print("\n=== 父级分割测试 ===")
    parent_separator = "\n\n"
    parent_chunks = test_content.split(parent_separator)
    parent_chunks = [chunk.strip() for chunk in parent_chunks if chunk.strip()]
    
    print(f"使用分隔符 '{parent_separator}' 分割")
    print(f"分割结果: {len(parent_chunks)} 个父块")
    
    for i, chunk in enumerate(parent_chunks):
        print(f"父块 {i+1} (长度: {len(chunk)}): {repr(chunk[:50])}")
    
    print("\n=== 子级分割测试 ===")
    child_separator = "\n"
    all_child_chunks = []
    
    for i, parent_chunk in enumerate(parent_chunks):
        print(f"\n对父块 {i+1} 进行子级分割:")
        child_chunks = parent_chunk.split(child_separator)
        child_chunks = [chunk.strip() for chunk in child_chunks if chunk.strip()]
        
        print(f"  子块数量: {len(child_chunks)}")
        for j, child_chunk in enumerate(child_chunks):
            print(f"    子块 {j+1}: {repr(child_chunk)}")
            all_child_chunks.append(child_chunk)
    
    print(f"\n=== 总结 ===")
    print(f"总父块数: {len(parent_chunks)}")
    print(f"总子块数: {len(all_child_chunks)}")
    
    # 验证期望结果
    if len(parent_chunks) == 4:
        print("✓ 父块数量正确 (4个章节)")
    else:
        print(f"✗ 父块数量错误: 期望4, 实际{len(parent_chunks)}")
    
    if len(all_child_chunks) > 10:
        print(f"✓ 子块数量合理 ({len(all_child_chunks)}个)")
    else:
        print(f"✗ 子块数量异常: {len(all_child_chunks)}个")

if __name__ == "__main__":
    print("开始测试分割逻辑...")
    test_split_logic()
    print("\n测试完成！")
