#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成测试用的JWT Token
"""

from datetime import datetime, timedelta, timezone
from jose import jwt
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app.core.config import settings

def create_token(email: str, expires_delta: timedelta):
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": email, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def main():
    # 创建一个有效期为30天的测试token
    email = "test@example.com"
    expires_delta = timedelta(days=30)
    token = create_token(email, expires_delta)
    
    print("\n=== 新创建的JWT Token ===")
    print(token)
    print("\n=== 可用于测试的CURL命令 ===")
    print(f"curl -X GET \"http://localhost:8000/api/v1/llm/discover?provider=lmstudio&url=http://0.0.0.0:1234\" \\\n  -H \"Authorization: Bearer {token}\" \\\n  -H \"Content-Type: application/json\"")
    
    # 将Token保存到.test_token文件中
    with open(".test_token", "w") as f:
        f.write(token)
    print("\nToken已保存到 .test_token 文件中")

if __name__ == "__main__":
    main() 