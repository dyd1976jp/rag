"""
索引管理器完整使用示例

本示例展示如何使用IndexProcessorFactory和ParentChildIndexProcessor进行完整的文档处理流程，
包括基础使用、配置示例、实际场景处理、性能测试等。

基于当前项目的RAG系统架构，参考Dify项目的实现模式。

注意：本示例使用模拟类来避免复杂的依赖关系，在实际使用时请替换为真实的导入。
"""

import asyncio
import logging
import time
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 模拟类定义 - 在实际使用时应该从真实模块导入
# ============================================================================

class ProcessorType:
    """处理器类型枚举"""
    PARENT_CHILD = "parent_child"
    SIMPLE = "simple"

class ProcessorConfig:
    """处理器配置类"""
    def __init__(self, enable_caching=True, cache_ttl_seconds=3600, max_concurrent_tasks=5):
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_concurrent_tasks = max_concurrent_tasks

class IndexProcessorFactory:
    """索引处理器工厂类"""
    def get_processor(self, processor_type=ProcessorType.PARENT_CHILD, config=None):
        if processor_type == ProcessorType.PARENT_CHILD:
            return ParentChildIndexProcessor()
        else:
            raise ValueError(f"不支持的处理器类型: {processor_type}")

class Document:
    """文档模型类"""
    def __init__(self, page_content="", metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}
        self.children = []

class ChildDocument:
    """子文档模型类"""
    def __init__(self, page_content="", metadata=None, parent_id=None):
        self.page_content = page_content
        self.metadata = metadata or {}
        self.parent_id = parent_id

class ExtractMode:
    """提取模式枚举"""
    TEXT = "text"
    PDF = "pdf"
    MARKDOWN = "markdown"

class ExtractSetting:
    """提取设置类"""
    def __init__(self, extract_mode=ExtractMode.TEXT, file_path=None, file_type=None,
                 extract_images=False, ocr_enabled=False):
        self.extract_mode = extract_mode
        self.file_path = file_path
        self.file_type = file_type
        self.extract_images = extract_images
        self.ocr_enabled = ocr_enabled

class ParentMode:
    """父文档模式枚举"""
    PARAGRAPH = "paragraph"
    FULL_DOC = "full_doc"

class Rule:
    """分割规则类"""
    def __init__(self, separator="\n", max_tokens=1000, chunk_overlap=200):
        self.separator = separator
        self.max_tokens = max_tokens
        self.chunk_overlap = chunk_overlap

class ProcessRule:
    """处理规则类"""
    def __init__(self, parent_mode=ParentMode.PARAGRAPH, segmentation=None, preview_mode=False):
        self.parent_mode = parent_mode
        self.segmentation = segmentation or Rule()
        self.preview_mode = preview_mode

class ParentChildIndexProcessor:
    """父子索引处理器类"""
    def __init__(self, vector_store=None, document_store=None, embedding_model=None, retrieval_service=None):
        self.vector_store = vector_store
        self.document_store = document_store
        self.embedding_model = embedding_model
        self.retrieval_service = retrieval_service

    def extract(self, extract_setting, **kwargs):
        """提取文档内容"""
        logger.info(f"提取文档: {extract_setting.file_path}")
        # 模拟提取过程
        return [Document(
            page_content="这是提取的文档内容。包含多个段落和丰富的信息。",
            metadata={"source": extract_setting.file_path or "test", "type": extract_setting.extract_mode}
        )]

    def transform(self, documents, process_rule, **kwargs):
        """转换文档为父子结构"""
        logger.info(f"转换 {len(documents)} 个文档")
        transformed = []

        for i, doc in enumerate(documents):
            # 创建父文档
            parent_doc = Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "doc_id": f"parent_{i}"}
            )

            # 模拟分割为子文档
            content = doc.page_content
            chunk_size = process_rule.segmentation.max_tokens
            overlap = process_rule.segmentation.chunk_overlap

            children = []
            start = 0
            child_id = 0

            while start < len(content):
                end = min(start + chunk_size, len(content))
                chunk_content = content[start:end]

                if chunk_content.strip():
                    child = ChildDocument(
                        page_content=chunk_content,
                        metadata={"parent_id": f"parent_{i}", "child_id": child_id},
                        parent_id=f"parent_{i}"
                    )
                    children.append(child)
                    child_id += 1

                # 确保进度，避免无限循环
                if end >= len(content):
                    break
                start = max(start + 1, end - overlap)

            parent_doc.children = children
            transformed.append(parent_doc)

        return transformed

    async def load(self, documents, batch_size=10, enable_parallel=False, **kwargs):
        """加载文档到存储系统"""
        logger.info(f"加载 {len(documents)} 个文档到存储系统")

        # 模拟加载过程
        total_children = sum(len(doc.children) for doc in documents if hasattr(doc, 'children'))

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            await asyncio.sleep(0.1)  # 模拟加载时间
            logger.info(f"已加载批次 {i//batch_size + 1}")

        return {
            "loaded_documents": len(documents),
            "loaded_children": total_children,
            "status": "success"
        }

    async def retrieve(self, query, top_k=5, score_threshold=0.5, **kwargs):
        """检索相关文档"""
        logger.info(f"检索查询: {query}")

        # 模拟检索过程
        await asyncio.sleep(0.1)

        # 返回模拟结果
        results = []
        for i in range(min(top_k, 3)):
            result = type('RetrievalResult', (), {
                'content': f'检索结果 {i+1}: 与"{query}"相关的内容片段',
                'score': 0.9 - i * 0.1,
                'metadata': {'source': f'doc_{i}', 'chunk_id': i}
            })()
            results.append(result)

        return results

    async def clean(self, **kwargs):
        """清理索引"""
        logger.info("清理索引数据")
        await asyncio.sleep(0.1)
        return {"cleaned": True}

# 模拟存储和服务类
class MilvusVectorStore:
    """Milvus向量存储模拟类"""
    def __init__(self, host="localhost", port="19530", collection_name="test", **kwargs):
        self.host = host
        self.port = port
        self.collection_name = collection_name

    async def initialize(self):
        logger.info("初始化Milvus向量存储")

    async def close(self):
        logger.info("关闭Milvus向量存储")

class DocumentStore:
    """文档存储模拟类"""
    def __init__(self, url="mongodb://localhost:27017", database="test", **kwargs):
        self.url = url
        self.database = database

    async def initialize(self):
        logger.info("初始化文档存储")

    async def close(self):
        logger.info("关闭文档存储")

class EmbeddingModel:
    """嵌入模型模拟类"""
    def __init__(self, model_name="text-embedding-ada-002", **kwargs):
        self.model_name = model_name

    async def initialize(self):
        logger.info("初始化嵌入模型")

    async def close(self):
        logger.info("关闭嵌入模型")

class RetrievalService:
    """检索服务模拟类"""
    def __init__(self, vector_store=None, document_store=None, **kwargs):
        self.vector_store = vector_store
        self.document_store = document_store

    async def initialize(self):
        logger.info("初始化检索服务")

# ============================================================================
# 配置类定义
# ============================================================================

@dataclass
class ExampleConfig:
    """示例配置类"""
    # MongoDB配置
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "rag_examples"

    # Milvus配置
    milvus_host: str = "localhost"
    milvus_port: str = "19530"
    milvus_collection: str = "example_collection"

    # 嵌入模型配置
    embedding_model_name: str = "text-embedding-ada-002"
    embedding_dimension: int = 1536

    # 分割配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separator: str = "\n"

    # 性能测试配置
    performance_target_seconds: float = 3.0
    test_document_count: int = 10


class IndexManagerUsageExample:
    """索引管理器使用示例类

    演示IndexProcessorFactory和ParentChildIndexProcessor的完整使用流程。
    """

    def __init__(self, config: Optional[ExampleConfig] = None):
        """初始化示例

        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or ExampleConfig()
        self.factory: Optional[IndexProcessorFactory] = None
        self.processor: Optional[ParentChildIndexProcessor] = None
        self.vector_store: Optional[MilvusVectorStore] = None
        self.document_store: Optional[DocumentStore] = None
        self.embedding_model: Optional[EmbeddingModel] = None
        self.retrieval_service: Optional[RetrievalService] = None

        logger.info("索引管理器使用示例初始化完成")

    async def setup_components(self) -> None:
        """设置和初始化所有组件

        包括向量存储、文档存储、嵌入模型和检索服务的初始化。
        """
        logger.info("开始设置组件...")

        try:
            # 初始化向量存储 (Milvus)
            self.vector_store = MilvusVectorStore(
                host=self.config.milvus_host,
                port=self.config.milvus_port,
                collection_name=self.config.milvus_collection,
                dimension=self.config.embedding_dimension
            )
            await self.vector_store.initialize()
            logger.info("Milvus向量存储初始化完成")

            # 初始化文档存储 (MongoDB)
            self.document_store = DocumentStore(
                connection_string=self.config.mongodb_url,
                database_name=self.config.mongodb_database
            )
            await self.document_store.initialize()
            logger.info("MongoDB文档存储初始化完成")

            # 初始化嵌入模型
            self.embedding_model = EmbeddingModel(
                model_name=self.config.embedding_model_name,
                dimension=self.config.embedding_dimension
            )
            await self.embedding_model.initialize()
            logger.info("嵌入模型初始化完成")

            # 初始化检索服务
            self.retrieval_service = RetrievalService(
                vector_store=self.vector_store,
                document_store=self.document_store,
                embedding_model=self.embedding_model
            )
            logger.info("检索服务初始化完成")

        except Exception as e:
            logger.error(f"组件设置失败: {str(e)}")
            raise

    def create_factory_and_processor(self) -> None:
        """创建工厂和处理器实例

        演示如何使用IndexProcessorFactory创建ParentChildIndexProcessor。
        """
        logger.info("创建工厂和处理器...")

        try:
            # 1. 创建工厂实例
            self.factory = IndexProcessorFactory()
            logger.info("IndexProcessorFactory创建成功")

            # 2. 配置处理器参数
            processor_config = ProcessorConfig(
                enable_caching=True,
                cache_ttl_seconds=3600,
                max_concurrent_tasks=5
            )

            # 3. 使用工厂创建处理器
            self.processor = self.factory.get_processor(
                processor_type=ProcessorType.PARENT_CHILD,
                config=processor_config
            )
            logger.info("ParentChildIndexProcessor创建成功")

            # 4. 或者直接创建处理器实例
            # self.processor = ParentChildIndexProcessor(
            #     vector_store=self.vector_store,
            #     document_store=self.document_store,
            #     embedding_model=self.embedding_model,
            #     retrieval_service=self.retrieval_service
            # )

        except Exception as e:
            logger.error(f"工厂和处理器创建失败: {str(e)}")
            raise

    async def basic_usage_example(self) -> Dict[str, Any]:
        """基础使用示例

        演示完整的文档处理流程：提取 -> 转换 -> 加载 -> 检索。

        Returns:
            Dict[str, Any]: 处理结果统计
        """
        logger.info("=== 基础使用示例开始 ===")

        try:
            # 1. 准备测试文档
            test_documents = self._create_test_documents()
            logger.info(f"准备了 {len(test_documents)} 个测试文档")

            # 2. 文档提取 (Extract)
            extract_setting = ExtractSetting(
                extract_mode=ExtractMode.TEXT,
                file_path="examples/test_document.txt",
                file_type="txt"
            )

            extracted_docs = self.processor.extract(extract_setting)
            logger.info(f"提取了 {len(extracted_docs)} 个文档")

            # 3. 文档转换为父子结构 (Transform)
            process_rule = ProcessRule(
                parent_mode=ParentMode.PARAGRAPH,
                segmentation=Rule(
                    separator=self.config.separator,
                    max_tokens=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap
                ),
                preview_mode=False
            )

            transformed_docs = self.processor.transform(
                documents=extracted_docs,
                process_rule=process_rule
            )
            logger.info(f"转换了 {len(transformed_docs)} 个父文档")

            # 统计子文档数量
            total_children = sum(len(doc.children) for doc in transformed_docs if hasattr(doc, 'children'))
            logger.info(f"生成了 {total_children} 个子文档")

            # 4. 加载到存储系统 (Load)
            await self.processor.load(
                documents=transformed_docs,
                batch_size=10,
                enable_parallel=True
            )
            logger.info("文档加载到存储系统完成")

            # 5. 检索测试 (Retrieve)
            query = "测试查询内容"
            retrieval_results = await self.processor.retrieve(
                query=query,
                top_k=5,
                score_threshold=0.7
            )
            logger.info(f"检索到 {len(retrieval_results)} 个相关文档")

            # 6. 返回处理结果统计
            result = {
                "extracted_documents": len(extracted_docs),
                "transformed_documents": len(transformed_docs),
                "total_child_documents": total_children,
                "retrieval_results": len(retrieval_results),
                "status": "success"
            }

            logger.info("=== 基础使用示例完成 ===")
            return result

        except Exception as e:
            logger.error(f"基础使用示例失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    def configuration_examples(self) -> Dict[str, Any]:
        """配置示例

        展示不同的分割策略配置和父子文档处理配置选项。

        Returns:
            Dict[str, Any]: 配置示例集合
        """
        logger.info("=== 配置示例开始 ===")

        configurations = {}

        # 1. 递归字符分割器配置
        configurations["recursive_splitter"] = {
            "name": "递归字符分割器",
            "config": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "separators": ["\n\n", "\n", "。", ".", " "],
                "keep_separator": True
            },
            "description": "适用于一般文本文档的分割"
        }

        # 2. 段落模式配置
        configurations["paragraph_mode"] = {
            "name": "段落模式父子文档",
            "config": {
                "parent_mode": ParentMode.PARAGRAPH,
                "segmentation": {
                    "separator": "\n",
                    "max_tokens": 2000,
                    "chunk_overlap": 100
                },
                "subchunk_segmentation": {
                    "separator": "。",
                    "max_tokens": 500,
                    "chunk_overlap": 50
                }
            },
            "description": "将段落作为父文档，句子作为子文档"
        }

        # 3. 全文档模式配置
        configurations["full_document_mode"] = {
            "name": "全文档模式父子文档",
            "config": {
                "parent_mode": ParentMode.FULL_DOC,
                "segmentation": {
                    "separator": "\n",
                    "max_tokens": 1000,
                    "chunk_overlap": 200
                }
            },
            "description": "整个文档作为父文档，分段作为子文档"
        }

        # 4. 预览模式配置
        configurations["preview_mode"] = {
            "name": "预览模式配置",
            "config": {
                "preview_mode": True,
                "preview_chunk_count": 5,
                "enable_content_preview": True,
                "preview_max_length": 200
            },
            "description": "用于文档上传前的预览"
        }

        # 5. 性能优化配置
        configurations["performance_optimized"] = {
            "name": "性能优化配置",
            "config": {
                "batch_size": 50,
                "enable_parallel": True,
                "max_concurrent_tasks": 10,
                "enable_caching": True,
                "cache_ttl_seconds": 7200
            },
            "description": "适用于大批量文档处理"
        }

        logger.info(f"生成了 {len(configurations)} 个配置示例")
        logger.info("=== 配置示例完成 ===")

        return configurations

    async def real_world_scenarios(self) -> Dict[str, Any]:
        """实际场景示例

        演示处理不同类型文档和预览模式与完整处理模式的区别。

        Returns:
            Dict[str, Any]: 各场景处理结果
        """
        logger.info("=== 实际场景示例开始 ===")

        scenarios = {}

        try:
            # 场景1: PDF文档处理
            scenarios["pdf_processing"] = await self._process_pdf_document()

            # 场景2: Markdown文档处理
            scenarios["markdown_processing"] = await self._process_markdown_document()

            # 场景3: 预览模式 vs 完整处理模式
            scenarios["preview_vs_full"] = await self._compare_preview_and_full_mode()

            # 场景4: 错误处理和异常情况
            scenarios["error_handling"] = await self._demonstrate_error_handling()

            # 场景5: 批量文档处理
            scenarios["batch_processing"] = await self._demonstrate_batch_processing()

            logger.info("=== 实际场景示例完成 ===")
            return scenarios

        except Exception as e:
            logger.error(f"实际场景示例失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def performance_and_testing_examples(self) -> Dict[str, Any]:
        """性能和测试示例

        展示性能基准测试和单元测试示例。

        Returns:
            Dict[str, Any]: 性能测试结果
        """
        logger.info("=== 性能和测试示例开始 ===")

        results = {}

        try:
            # 1. 性能基准测试
            results["performance_benchmark"] = await self._run_performance_benchmark()

            # 2. 检索时间测试
            results["retrieval_performance"] = await self._test_retrieval_performance()

            # 3. 索引质量验证
            results["index_quality"] = await self._validate_index_quality()

            # 4. 并发处理测试
            results["concurrent_processing"] = await self._test_concurrent_processing()

            # 5. 内存使用监控
            results["memory_usage"] = self._monitor_memory_usage()

            logger.info("=== 性能和测试示例完成 ===")
            return results

        except Exception as e:
            logger.error(f"性能和测试示例失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _create_test_documents(self) -> List[Document]:
        """创建测试文档

        Returns:
            List[Document]: 测试文档列表
        """
        documents = []

        # 创建不同类型的测试文档
        test_contents = [
            "这是第一个测试文档。它包含了一些基本的文本内容，用于测试文档分割和索引功能。",
            "第二个文档包含更多的内容。\n\n它有多个段落，每个段落都有不同的主题。\n\n这样可以更好地测试父子文档的分割效果。",
            "技术文档示例：\n1. 系统架构设计\n2. API接口规范\n3. 数据库设计\n4. 部署指南\n\n每个部分都包含详细的说明和示例代码。",
            "长文档测试：" + "这是一个很长的句子，用于测试文档分割器在处理长文本时的表现。" * 20,
            "特殊字符测试：包含各种标点符号！@#$%^&*()，以及中英文混合内容 English mixed content。"
        ]

        for i, content in enumerate(test_contents):
            doc = Document(
                page_content=content,
                metadata={
                    "source": f"test_document_{i+1}",
                    "type": "test",
                    "created_at": time.time(),
                    "length": len(content)
                }
            )
            documents.append(doc)

        return documents

    async def _process_pdf_document(self) -> Dict[str, Any]:
        """处理PDF文档示例"""
        logger.info("处理PDF文档...")

        # 模拟PDF文档处理
        extract_setting = ExtractSetting(
            extract_mode=ExtractMode.PDF,
            file_path="examples/sample.pdf",
            file_type="pdf",
            extract_images=True,
            ocr_enabled=True
        )

        try:
            # 这里应该是实际的PDF处理逻辑
            # extracted_docs = self.processor.extract(extract_setting)

            # 模拟结果
            result = {
                "document_type": "PDF",
                "pages_processed": 5,
                "text_extracted": True,
                "images_extracted": 3,
                "ocr_applied": True,
                "processing_time": 2.5,
                "status": "success"
            }

            logger.info("PDF文档处理完成")
            return result

        except Exception as e:
            logger.error(f"PDF文档处理失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _process_markdown_document(self) -> Dict[str, Any]:
        """处理Markdown文档示例"""
        logger.info("处理Markdown文档...")

        markdown_content = """
# 标题一
这是第一个段落的内容。

## 标题二
这是第二个段落的内容，包含一些**粗体**和*斜体*文本。

### 标题三
- 列表项1
- 列表项2
- 列表项3

```python
# 代码块示例
def hello_world():
    print("Hello, World!")
```

> 这是一个引用块
> 包含多行内容
        """

        try:
            doc = Document(
                page_content=markdown_content,
                metadata={
                    "source": "sample.md",
                    "type": "markdown",
                    "has_code_blocks": True,
                    "has_lists": True
                }
            )

            # 处理Markdown文档
            process_rule = ProcessRule(
                parent_mode=ParentMode.PARAGRAPH,
                segmentation=Rule(
                    separator="\n\n",
                    max_tokens=500,
                    chunk_overlap=50
                )
            )

            transformed_docs = self.processor.transform([doc], process_rule)

            result = {
                "document_type": "Markdown",
                "original_length": len(markdown_content),
                "parent_documents": len(transformed_docs),
                "child_documents": sum(len(d.children) for d in transformed_docs if hasattr(d, 'children')),
                "has_code_blocks": True,
                "has_structured_content": True,
                "status": "success"
            }

            logger.info("Markdown文档处理完成")
            return result

        except Exception as e:
            logger.error(f"Markdown文档处理失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _compare_preview_and_full_mode(self) -> Dict[str, Any]:
        """比较预览模式和完整处理模式"""
        logger.info("比较预览模式和完整处理模式...")

        test_doc = Document(
            page_content="这是一个测试文档。" * 100,  # 创建较长的文档
            metadata={"source": "comparison_test", "type": "test"}
        )

        try:
            # 预览模式处理
            preview_rule = ProcessRule(
                parent_mode=ParentMode.PARAGRAPH,
                segmentation=Rule(separator="\n", max_tokens=200, chunk_overlap=50),
                preview_mode=True
            )

            start_time = time.time()
            preview_docs = self.processor.transform([test_doc], preview_rule)
            preview_time = time.time() - start_time

            # 完整处理模式
            full_rule = ProcessRule(
                parent_mode=ParentMode.PARAGRAPH,
                segmentation=Rule(separator="\n", max_tokens=200, chunk_overlap=50),
                preview_mode=False
            )

            start_time = time.time()
            full_docs = self.processor.transform([test_doc], full_rule)
            full_time = time.time() - start_time

            result = {
                "preview_mode": {
                    "documents_count": len(preview_docs),
                    "processing_time": preview_time,
                    "limited_output": True
                },
                "full_mode": {
                    "documents_count": len(full_docs),
                    "processing_time": full_time,
                    "complete_output": True
                },
                "performance_difference": {
                    "time_ratio": full_time / preview_time if preview_time > 0 else 0,
                    "document_ratio": len(full_docs) / len(preview_docs) if len(preview_docs) > 0 else 0
                },
                "status": "success"
            }

            logger.info("预览模式和完整处理模式比较完成")
            return result

        except Exception as e:
            logger.error(f"模式比较失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _demonstrate_error_handling(self) -> Dict[str, Any]:
        """演示错误处理和异常情况"""
        logger.info("演示错误处理...")

        error_cases = {}

        # 1. 空文档处理
        try:
            empty_doc = Document(page_content="", metadata={})
            result = self.processor.transform([empty_doc], ProcessRule())
            error_cases["empty_document"] = {"status": "handled", "result_count": len(result)}
        except Exception as e:
            error_cases["empty_document"] = {"status": "error", "error": str(e)}

        # 2. 无效配置处理
        try:
            invalid_rule = ProcessRule(
                segmentation=Rule(max_tokens=-1, chunk_overlap=200)  # 无效配置
            )
            test_doc = Document(page_content="测试内容", metadata={})
            result = self.processor.transform([test_doc], invalid_rule)
            error_cases["invalid_config"] = {"status": "handled", "result_count": len(result)}
        except Exception as e:
            error_cases["invalid_config"] = {"status": "error", "error": str(e)}

        # 3. 超大文档处理
        try:
            large_content = "这是一个超大文档。" * 10000
            large_doc = Document(page_content=large_content, metadata={})
            start_time = time.time()
            result = self.processor.transform([large_doc], ProcessRule())
            processing_time = time.time() - start_time
            error_cases["large_document"] = {
                "status": "handled",
                "result_count": len(result),
                "processing_time": processing_time,
                "content_length": len(large_content)
            }
        except Exception as e:
            error_cases["large_document"] = {"status": "error", "error": str(e)}

        return error_cases

    async def _demonstrate_batch_processing(self) -> Dict[str, Any]:
        """演示批量文档处理"""
        logger.info("演示批量文档处理...")

        try:
            # 创建批量测试文档
            batch_docs = []
            for i in range(self.config.test_document_count):
                doc = Document(
                    page_content=f"批量测试文档 {i+1}。" + "内容重复。" * 50,
                    metadata={"source": f"batch_doc_{i+1}", "batch_id": "test_batch"}
                )
                batch_docs.append(doc)

            start_time = time.time()

            # 批量转换
            process_rule = ProcessRule(
                parent_mode=ParentMode.PARAGRAPH,
                segmentation=Rule(separator="。", max_tokens=300, chunk_overlap=50)
            )

            transformed_docs = self.processor.transform(batch_docs, process_rule)

            # 批量加载
            await self.processor.load(
                documents=transformed_docs,
                batch_size=5,
                enable_parallel=True
            )

            processing_time = time.time() - start_time

            result = {
                "input_documents": len(batch_docs),
                "output_documents": len(transformed_docs),
                "total_child_documents": sum(len(d.children) for d in transformed_docs if hasattr(d, 'children')),
                "processing_time": processing_time,
                "average_time_per_doc": processing_time / len(batch_docs),
                "status": "success"
            }

            logger.info("批量文档处理完成")
            return result

        except Exception as e:
            logger.error(f"批量处理失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _run_performance_benchmark(self) -> Dict[str, Any]:
        """运行性能基准测试"""
        logger.info("运行性能基准测试...")

        try:
            # 创建基准测试文档
            benchmark_doc = Document(
                page_content="性能测试文档内容。" * 1000,
                metadata={"source": "benchmark", "type": "performance_test"}
            )

            # 测试不同配置的性能
            configurations = [
                {"chunk_size": 500, "overlap": 50},
                {"chunk_size": 1000, "overlap": 100},
                {"chunk_size": 2000, "overlap": 200}
            ]

            results = {}

            for i, config in enumerate(configurations):
                start_time = time.time()

                rule = ProcessRule(
                    parent_mode=ParentMode.PARAGRAPH,
                    segmentation=Rule(
                        separator="\n",
                        max_tokens=config["chunk_size"],
                        chunk_overlap=config["overlap"]
                    )
                )

                transformed = self.processor.transform([benchmark_doc], rule)
                processing_time = time.time() - start_time

                results[f"config_{i+1}"] = {
                    "chunk_size": config["chunk_size"],
                    "chunk_overlap": config["overlap"],
                    "processing_time": processing_time,
                    "output_documents": len(transformed),
                    "meets_target": processing_time < self.config.performance_target_seconds
                }

            return results

        except Exception as e:
            logger.error(f"性能基准测试失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _test_retrieval_performance(self) -> Dict[str, Any]:
        """测试检索性能"""
        logger.info("测试检索性能...")

        try:
            queries = [
                "测试查询1",
                "性能基准测试",
                "文档处理流程",
                "索引管理器使用",
                "RAG系统架构"
            ]

            retrieval_times = []

            for query in queries:
                start_time = time.time()
                results = await self.processor.retrieve(
                    query=query,
                    top_k=10,
                    score_threshold=0.5
                )
                retrieval_time = time.time() - start_time
                retrieval_times.append(retrieval_time)

            avg_time = sum(retrieval_times) / len(retrieval_times)
            max_time = max(retrieval_times)
            min_time = min(retrieval_times)

            return {
                "queries_tested": len(queries),
                "average_retrieval_time": avg_time,
                "max_retrieval_time": max_time,
                "min_retrieval_time": min_time,
                "meets_target": avg_time < self.config.performance_target_seconds,
                "all_times": retrieval_times
            }

        except Exception as e:
            logger.error(f"检索性能测试失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _validate_index_quality(self) -> Dict[str, Any]:
        """验证索引质量"""
        logger.info("验证索引质量...")

        try:
            # 创建已知内容的测试文档
            test_content = "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。"
            test_doc = Document(
                page_content=test_content,
                metadata={"source": "quality_test", "known_content": True}
            )

            # 处理并索引文档
            rule = ProcessRule(
                parent_mode=ParentMode.PARAGRAPH,
                segmentation=Rule(separator="。", max_tokens=100, chunk_overlap=20)
            )

            transformed = self.processor.transform([test_doc], rule)
            await self.processor.load(transformed)

            # 测试相关查询的检索质量
            relevant_queries = [
                "人工智能",
                "计算机科学",
                "智能系统"
            ]

            quality_scores = []

            for query in relevant_queries:
                results = await self.processor.retrieve(query, top_k=5)
                # 检查是否检索到相关内容
                found_relevant = any("人工智能" in result.content or "计算机" in result.content
                                   for result in results)
                quality_scores.append(1.0 if found_relevant else 0.0)

            avg_quality = sum(quality_scores) / len(quality_scores)

            return {
                "test_queries": len(relevant_queries),
                "average_quality_score": avg_quality,
                "quality_threshold_met": avg_quality >= 0.8,
                "individual_scores": quality_scores
            }

        except Exception as e:
            logger.error(f"索引质量验证失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _test_concurrent_processing(self) -> Dict[str, Any]:
        """测试并发处理"""
        logger.info("测试并发处理...")

        try:
            # 创建多个并发任务
            async def process_single_doc(doc_id: int) -> Dict[str, Any]:
                doc = Document(
                    page_content=f"并发测试文档 {doc_id}。" + "内容重复。" * 20,
                    metadata={"source": f"concurrent_doc_{doc_id}", "doc_id": doc_id}
                )

                start_time = time.time()
                rule = ProcessRule(
                    parent_mode=ParentMode.PARAGRAPH,
                    segmentation=Rule(separator="。", max_tokens=200, chunk_overlap=50)
                )

                result = self.processor.transform([doc], rule)
                processing_time = time.time() - start_time

                return {
                    "doc_id": doc_id,
                    "processing_time": processing_time,
                    "output_count": len(result)
                }

            # 并发执行多个任务
            concurrent_tasks = 5
            tasks = [process_single_doc(i) for i in range(concurrent_tasks)]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            return {
                "concurrent_tasks": concurrent_tasks,
                "total_processing_time": total_time,
                "average_task_time": sum(r["processing_time"] for r in results) / len(results),
                "successful_tasks": len([r for r in results if "error" not in r]),
                "task_results": results
            }

        except Exception as e:
            logger.error(f"并发处理测试失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _monitor_memory_usage(self) -> Dict[str, Any]:
        """监控内存使用"""
        logger.info("监控内存使用...")

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "rss_memory_mb": memory_info.rss / 1024 / 1024,
                "vms_memory_mb": memory_info.vms / 1024 / 1024,
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent()
            }

        except ImportError:
            logger.warning("psutil未安装，无法监控内存使用")
            return {"status": "unavailable", "reason": "psutil not installed"}
        except Exception as e:
            logger.error(f"内存监控失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("清理资源...")

        try:
            if self.vector_store:
                await self.vector_store.close()

            if self.document_store:
                await self.document_store.close()

            if self.embedding_model:
                await self.embedding_model.close()

            logger.info("资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {str(e)}")


async def main():
    """主函数 - 运行所有示例"""
    logger.info("开始运行索引管理器使用示例")

    # 创建示例实例
    example = IndexManagerUsageExample()

    try:
        # 1. 设置组件
        await example.setup_components()

        # 2. 创建工厂和处理器
        example.create_factory_and_processor()

        # 3. 运行基础使用示例
        logger.info("\n" + "="*50)
        logger.info("运行基础使用示例")
        basic_results = await example.basic_usage_example()
        print(f"基础使用结果: {basic_results}")

        # 4. 展示配置示例
        logger.info("\n" + "="*50)
        logger.info("展示配置示例")
        config_examples = example.configuration_examples()
        print(f"配置示例数量: {len(config_examples)}")

        # 5. 运行实际场景示例
        logger.info("\n" + "="*50)
        logger.info("运行实际场景示例")
        scenario_results = await example.real_world_scenarios()
        print(f"场景测试结果: {scenario_results}")

        # 6. 运行性能和测试示例
        logger.info("\n" + "="*50)
        logger.info("运行性能和测试示例")
        performance_results = await example.performance_and_testing_examples()
        print(f"性能测试结果: {performance_results}")

        logger.info("\n" + "="*50)
        logger.info("所有示例运行完成！")

    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}")
        raise

    finally:
        # 清理资源
        await example.cleanup()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())