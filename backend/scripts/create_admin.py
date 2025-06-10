#!/usr/bin/env python
"""
创建管理员用户脚本

此脚本用于创建具有管理员权限的用户，可以在系统初始化或需要时运行。
管理员用户可以管理所有文档，包括删除任何用户的文档。

使用方法:
python -m scripts.create_admin --email admin@example.com --username admin --password securepassword
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from bson import ObjectId

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.mongodb import mongodb
from app.core.security import get_password_hash
from app.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_admin_user(email: str, username: str, password: str):
    """创建管理员用户"""
    try:
        # 连接到MongoDB
        await mongodb.connect_to_database()
        logger.info(f"已连接到数据库: {settings.MONGODB_DB}")
        
        # 检查用户是否已存在
        existing_user = await mongodb.db.users.find_one({"email": email})
        if existing_user:
            logger.info(f"用户 {email} 已存在，更新为管理员权限")
            
            # 更新为管理员
            result = await mongodb.db.users.update_one(
                {"email": email},
                {"$set": {
                    "is_admin": True,
                    "is_superuser": True,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count:
                logger.info(f"已将用户 {email} 更新为管理员")
            else:
                logger.warning(f"用户 {email} 已经是管理员，无需更新")
                
            return
        
        # 创建新管理员用户
        hashed_password = get_password_hash(password)
        now = datetime.utcnow()
        
        user_data = {
            "_id": ObjectId(),
            "email": email,
            "username": username,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_superuser": True,
            "is_admin": True,
            "created_at": now,
            "updated_at": now
        }
        
        result = await mongodb.db.users.insert_one(user_data)
        
        if result.inserted_id:
            logger.info(f"成功创建管理员用户: {email}")
        else:
            logger.error("创建管理员用户失败")
            
    except Exception as e:
        logger.error(f"创建管理员用户时出错: {str(e)}")
        raise
    finally:
        # 关闭数据库连接
        await mongodb.close_database_connection()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="创建管理员用户")
    parser.add_argument("--email", required=True, help="管理员邮箱")
    parser.add_argument("--username", required=True, help="管理员用户名")
    parser.add_argument("--password", required=True, help="管理员密码")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(create_admin_user(args.email, args.username, args.password))
    logger.info("脚本执行完成") 