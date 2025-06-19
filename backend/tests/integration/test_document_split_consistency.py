#!/usr/bin/env python3
"""
测试文档分割一致性的脚本
验证 preview-split 和 upload (preview_only=true) 端点是否产生一致的结果
"""

import requests
import json
import sys
import os

# 测试配置
BASE_URL = "http://localhost:8000/api/v1/rag"
TEST_FILE_PATH = "初赛训练数据集.pdf"  # 请确保这个文件存在

# 测试参数
TEST_PARAMS = {
    "parent_chunk_size": 1024,
    "parent_chunk_overlap": 200,
    "parent_separator": "\n\n",
    "child_chunk_size": 512,
    "child_chunk_overlap": 50,
    "child_separator": "\n"
}

def get_auth_token():
    """获取认证token"""
    # 这里需要根据你的认证系统调整
    # 假设有一个登录端点
    login_url = "http://localhost:8000/api/v1/auth/login"
    login_data = {
        "email": "test@example.com",  # 请替换为实际的测试用户
        "password": "testpassword"    # 请替换为实际的测试密码
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"登录请求失败: {e}")
        return None

def test_preview_split_endpoint(token, file_path):
    """测试 preview-split 端点"""
    url = f"{BASE_URL}/documents/preview-split"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = TEST_PARAMS
        
        try:
            response = requests.post(url, headers=headers, files=files, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"preview-split 请求失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"preview-split 请求异常: {e}")
            return None

def test_upload_preview_endpoint(token, file_path):
    """测试 upload 端点的预览模式"""
    url = f"{BASE_URL}/documents/upload"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {**TEST_PARAMS, "preview_only": True}
        
        try:
            response = requests.post(url, headers=headers, files=files, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"upload preview 请求失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"upload preview 请求异常: {e}")
            return None

def compare_results(preview_result, upload_result):
    """比较两个端点的结果"""
    print("=" * 60)
    print("结果比较")
    print("=" * 60)
    
    if not preview_result or not upload_result:
        print("❌ 无法比较结果，因为有端点请求失败")
        return False
    
    # 比较基本信息
    preview_segments = preview_result.get("segments", [])
    upload_segments = upload_result.get("segments", [])
    
    print(f"preview-split 段落数: {len(preview_segments)}")
    print(f"upload preview 段落数: {len(upload_segments)}")
    
    if len(preview_segments) != len(upload_segments):
        print("❌ 段落数量不一致")
        return False
    
    # 比较每个段落的内容
    all_match = True
    for i, (p_seg, u_seg) in enumerate(zip(preview_segments, upload_segments)):
        p_content = p_seg.get("content", "")
        u_content = u_seg.get("content", "")
        
        if p_content != u_content:
            print(f"❌ 段落 {i+1} 内容不一致")
            print(f"  preview-split: {p_content[:100]}...")
            print(f"  upload preview: {u_content[:100]}...")
            all_match = False
        
        # 比较子段落
        p_children = p_seg.get("children", [])
        u_children = u_seg.get("children", [])
        
        if len(p_children) != len(u_children):
            print(f"❌ 段落 {i+1} 子段落数量不一致: {len(p_children)} vs {len(u_children)}")
            all_match = False
        else:
            for j, (p_child, u_child) in enumerate(zip(p_children, u_children)):
                p_child_content = p_child.get("content", "")
                u_child_content = u_child.get("content", "")
                
                if p_child_content != u_child_content:
                    print(f"❌ 段落 {i+1} 子段落 {j+1} 内容不一致")
                    print(f"  preview-split: {p_child_content[:50]}...")
                    print(f"  upload preview: {u_child_content[:50]}...")
                    all_match = False
    
    if all_match:
        print("✅ 所有段落内容完全一致")
        return True
    else:
        print("❌ 存在内容不一致的段落")
        return False

def main():
    """主函数"""
    print("开始测试文档分割一致性...")
    
    # 检查测试文件是否存在
    if not os.path.exists(TEST_FILE_PATH):
        print(f"❌ 测试文件不存在: {TEST_FILE_PATH}")
        print("请确保测试文件存在，或修改 TEST_FILE_PATH 变量")
        return False
    
    # 获取认证token
    print("获取认证token...")
    token = get_auth_token()
    if not token:
        print("❌ 无法获取认证token，请检查登录信息")
        return False
    
    print("✅ 认证成功")
    
    # 测试 preview-split 端点
    print("\n测试 preview-split 端点...")
    preview_result = test_preview_split_endpoint(token, TEST_FILE_PATH)
    
    # 测试 upload 端点的预览模式
    print("测试 upload 端点的预览模式...")
    upload_result = test_upload_preview_endpoint(token, TEST_FILE_PATH)
    
    # 比较结果
    success = compare_results(preview_result, upload_result)
    
    if success:
        print("\n🎉 测试通过！两个端点产生了一致的结果")
        return True
    else:
        print("\n❌ 测试失败！两个端点产生了不一致的结果")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
