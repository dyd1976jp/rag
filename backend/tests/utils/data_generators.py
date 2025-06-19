"""
测试数据生成器

提供各种测试数据的生成函数，用于创建一致的测试数据。
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

try:
    from faker import Faker
    fake = Faker(['zh_CN', 'en_US'])
    HAS_FAKER = True
except ImportError:
    # 如果没有安装faker，使用简单的替代实现
    HAS_FAKER = False

    class SimpleFaker:
        """简单的Faker替代实现"""

        def sentence(self, nb_words: int = 6) -> str:
            words = ["这是", "一个", "测试", "文档", "内容", "示例", "数据", "生成", "功能", "模块"]
            return "".join(random.choices(words, k=nb_words)) + "。"

        def paragraph(self, nb_sentences: int = 3) -> str:
            sentences = [self.sentence() for _ in range(nb_sentences)]
            return "".join(sentences)

        def name(self) -> str:
            names = ["张三", "李四", "王五", "赵六", "钱七", "孙八"]
            return random.choice(names)

        def email(self) -> str:
            domains = ["example.com", "test.com", "demo.com"]
            names = ["user", "test", "demo", "admin"]
            return f"{random.choice(names)}{random.randint(1, 999)}@{random.choice(domains)}"

        def user_name(self) -> str:
            return f"user{random.randint(1000, 9999)}"

        def file_name(self, extension: str = 'txt') -> str:
            names = ["document", "file", "test", "sample", "demo"]
            return f"{random.choice(names)}{random.randint(1, 999)}.{extension}"

    fake = SimpleFaker()


class DocumentDataGenerator:
    """文档数据生成器"""
    
    @staticmethod
    def generate_simple_text() -> str:
        """
        生成简单的测试文本
        
        Returns:
            str: 测试文本
        """
        return """第一章：引言

这是第一章的内容。它包含多行文本，用于测试文档分割功能。
这里有一些基本的介绍信息。

第二章：方法

这是第二章的内容。包含了详细的方法描述。
这里有更多的技术细节和实现方案。

第三章：结果

实验结果如下：
1. 结果一：性能提升显著
2. 结果二：准确率达到95%
3. 结果三：用户满意度高

第四章：总结

总结内容在这里。这是项目的最终结论。"""
    
    @staticmethod
    def generate_long_text(paragraphs: int = 10) -> str:
        """
        生成长文本
        
        Args:
            paragraphs: 段落数量
            
        Returns:
            str: 长文本
        """
        content = []
        for i in range(paragraphs):
            title = f"第{i+1}章：{fake.sentence(nb_words=3)}"
            content.append(title)
            content.append("")  # 空行
            
            # 生成段落内容
            for _ in range(random.randint(2, 5)):
                content.append(fake.paragraph(nb_sentences=random.randint(3, 6)))
            content.append("")  # 段落间空行
        
        return "\n".join(content)
    
    @staticmethod
    def generate_structured_text() -> str:
        """
        生成结构化文本（包含列表、标题等）
        
        Returns:
            str: 结构化文本
        """
        return """# 项目文档

## 1. 概述

本项目是一个RAG（检索增强生成）系统，旨在提供高质量的文档问答服务。

### 1.1 主要功能
- 文档上传和处理
- 智能文档分割
- 向量化存储
- 语义搜索
- 智能问答

### 1.2 技术栈
- 后端：FastAPI + Python
- 数据库：MongoDB + Milvus
- AI模型：OpenAI GPT + Embedding

## 2. 系统架构

### 2.1 整体架构
系统采用微服务架构，包含以下主要组件：

1. **API网关**：负责请求路由和认证
2. **文档处理服务**：处理文档上传和分割
3. **向量存储服务**：管理文档向量化和检索
4. **问答服务**：提供智能问答功能

### 2.2 数据流
1. 用户上传文档
2. 系统进行文档预处理
3. 文档分割成小块
4. 向量化并存储
5. 用户提问时进行语义搜索
6. 结合检索结果生成答案

## 3. API接口

### 3.1 文档管理
- POST /api/v1/rag/documents/upload - 上传文档
- GET /api/v1/rag/documents - 获取文档列表
- DELETE /api/v1/rag/documents/{id} - 删除文档

### 3.2 问答接口
- POST /api/v1/rag/chat - 智能问答
- POST /api/v1/rag/search - 文档搜索

## 4. 部署说明

### 4.1 环境要求
- Python 3.8+
- MongoDB 4.4+
- Milvus 2.0+
- Redis 6.0+

### 4.2 安装步骤
1. 克隆代码仓库
2. 安装依赖包
3. 配置环境变量
4. 启动服务

## 5. 常见问题

### 5.1 文档上传失败
检查文件格式是否支持，当前支持：
- PDF文件
- TXT文件
- Markdown文件

### 5.2 搜索结果不准确
可能的原因：
- 文档质量较低
- 分割参数不合适
- 向量模型不匹配

## 6. 更新日志

### v1.0.0 (2024-06-17)
- 初始版本发布
- 支持基本的文档上传和问答功能

### v1.1.0 (计划中)
- 支持更多文档格式
- 优化分割算法
- 提升问答准确率"""
    
    @staticmethod
    def generate_document_metadata(doc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成文档元数据
        
        Args:
            doc_id: 文档ID，如果不提供则自动生成
            
        Returns:
            Dict: 文档元数据
        """
        return {
            "doc_id": doc_id or str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "file_name": fake.file_name(extension='txt'),
            "source": "test",
            "created_at": datetime.now().isoformat(),
            "file_size": random.randint(1000, 100000),
            "language": "zh-CN",
            "author": fake.name(),
            "title": fake.sentence(nb_words=5)
        }


class APIResponseGenerator:
    """API响应数据生成器"""
    
    @staticmethod
    def generate_document_upload_response(success: bool = True) -> Dict[str, Any]:
        """
        生成文档上传响应
        
        Args:
            success: 是否成功
            
        Returns:
            Dict: 上传响应
        """
        if success:
            return {
                "success": True,
                "message": "文档上传成功",
                "doc_id": str(uuid.uuid4()),
                "segments_count": random.randint(5, 20)
            }
        else:
            return {
                "success": False,
                "message": "文档上传失败",
                "error": "文件格式不支持"
            }
    
    @staticmethod
    def generate_document_split_response(segments_count: int = 5) -> Dict[str, Any]:
        """
        生成文档分割响应
        
        Args:
            segments_count: 段落数量
            
        Returns:
            Dict: 分割响应
        """
        segments = []
        children_content = []
        
        for i in range(segments_count):
            children = []
            for j in range(random.randint(2, 4)):
                child_content = fake.paragraph(nb_sentences=3)
                children.append({
                    "id": f"{i}_{j}",
                    "content": child_content,
                    "start": 0,
                    "end": len(child_content),
                    "length": len(child_content)
                })
                children_content.append(child_content)
            
            parent_content = "\n".join([child["content"] for child in children])
            segments.append({
                "id": i,
                "content": parent_content,
                "start": 0,
                "end": len(parent_content),
                "length": len(parent_content),
                "children": children
            })
        
        return {
            "success": True,
            "segments": segments,
            "total_segments": segments_count,
            "parentContent": "\n\n".join([seg["content"] for seg in segments]),
            "childrenContent": children_content
        }
    
    @staticmethod
    def generate_llm_discovery_response(model_count: int = 3) -> List[Dict[str, Any]]:
        """
        生成LLM发现响应
        
        Args:
            model_count: 模型数量
            
        Returns:
            List: 模型列表
        """
        models = []
        for i in range(model_count):
            models.append({
                "id": f"model-{i+1}",
                "name": f"Test Model {i+1}",
                "context_window": random.choice([4096, 8192, 16384]),
                "description": fake.sentence(nb_words=8)
            })
        return models
    
    @staticmethod
    def generate_chat_response(question: str) -> Dict[str, Any]:
        """
        生成聊天响应
        
        Args:
            question: 用户问题
            
        Returns:
            Dict: 聊天响应
        """
        return {
            "success": True,
            "answer": fake.paragraph(nb_sentences=3),
            "sources": [
                {
                    "doc_id": str(uuid.uuid4()),
                    "content": fake.paragraph(nb_sentences=2),
                    "score": random.uniform(0.7, 0.95)
                }
                for _ in range(random.randint(1, 3))
            ],
            "question": question,
            "timestamp": datetime.now().isoformat()
        }


class UserDataGenerator:
    """用户数据生成器"""
    
    @staticmethod
    def generate_user_data() -> Dict[str, Any]:
        """
        生成用户数据
        
        Returns:
            Dict: 用户数据
        """
        return {
            "id": str(uuid.uuid4()),
            "email": fake.email(),
            "username": fake.user_name(),
            "full_name": fake.name(),
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "last_login": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        }
    
    @staticmethod
    def generate_auth_token() -> str:
        """
        生成认证令牌
        
        Returns:
            str: JWT令牌
        """
        # 这是一个模拟的JWT令牌，实际测试中应该使用真实的令牌生成逻辑
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.test_token_signature"


class ConfigDataGenerator:
    """配置数据生成器"""
    
    @staticmethod
    def generate_split_config() -> Dict[str, Any]:
        """
        生成分割配置
        
        Returns:
            Dict: 分割配置
        """
        return {
            "parent_chunk_size": random.choice([512, 1024, 2048]),
            "parent_chunk_overlap": random.choice([50, 100, 200]),
            "parent_separator": random.choice(["\n\n", "\n", "。"]),
            "child_chunk_size": random.choice([256, 512, 1024]),
            "child_chunk_overlap": random.choice([25, 50, 100]),
            "child_separator": random.choice(["\n", "。", ". "])
        }
    
    @staticmethod
    def generate_llm_config() -> Dict[str, Any]:
        """
        生成LLM配置
        
        Returns:
            Dict: LLM配置
        """
        return {
            "provider": random.choice(["openai", "local", "azure"]),
            "model_type": random.choice(["gpt-3.5-turbo", "gpt-4", "local-model"]),
            "temperature": random.uniform(0.0, 1.0),
            "max_tokens": random.choice([1000, 2000, 4000]),
            "context_window": random.choice([4096, 8192, 16384])
        }


# 全局生成器实例
doc_generator = DocumentDataGenerator()
api_generator = APIResponseGenerator()
user_generator = UserDataGenerator()
config_generator = ConfigDataGenerator()
