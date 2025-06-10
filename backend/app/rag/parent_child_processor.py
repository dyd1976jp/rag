import re
import uuid
import logging
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel
from .models import Document, ChildDocument
from .text_splitter import FixedRecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class ParentMode(str, Enum):
    """父文档分割模式"""
    PARAGRAPH = "paragraph"

class Segmentation(BaseModel):
    """分段配置"""
    separator: str = "\n"
    max_tokens: int = 4000
    chunk_overlap: int = 200

class ProcessingRule(BaseModel):
    """处理规则"""
    parent_mode: ParentMode = ParentMode.PARAGRAPH
    segmentation: Segmentation = Segmentation()
    subchunk_segmentation: Optional[Segmentation] = None

class ProcessingError(Exception):
    """处理错误"""
    pass

class ParentChildIndexProcessor:
    """父子文档索引处理器"""
    
    def __init__(self):
        self.default_rule = ProcessingRule()
    
    def transform(self, documents: List[Document], rule: Optional[ProcessingRule] = None) -> List[Document]:
        """转换文档为父子结构"""
        try:
            if not documents:
                logger.warning("没有文档需要处理")
                return []
                
            rule = rule or self.default_rule
            logger.info(f"使用处理规则: {rule.dict()}")
            
            all_documents = []
            
            if rule.parent_mode == ParentMode.PARAGRAPH:
                # 获取父文档分词器
                parent_splitter = FixedRecursiveCharacterTextSplitter(
                    chunk_size=rule.segmentation.max_tokens,
                    chunk_overlap=rule.segmentation.chunk_overlap,
                    separators=[rule.segmentation.separator]
                )
                logger.info(f"创建父文档分词器: chunk_size={rule.segmentation.max_tokens}, "
                          f"overlap={rule.segmentation.chunk_overlap}")
                
                # 获取子文档分词器
                child_splitter = None
                if rule.subchunk_segmentation:
                    child_splitter = FixedRecursiveCharacterTextSplitter(
                        chunk_size=rule.subchunk_segmentation.max_tokens,
                        chunk_overlap=rule.subchunk_segmentation.chunk_overlap,
                        separators=[rule.subchunk_segmentation.separator]
                    )
                    logger.info(f"创建子文档分词器: chunk_size={rule.subchunk_segmentation.max_tokens}, "
                              f"overlap={rule.subchunk_segmentation.chunk_overlap}")
                
                for document in documents:
                    try:
                        # 清理文档内容
                        document_text = self._clean_text(document.page_content)
                        if not document_text:
                            logger.warning(f"文档内容为空，跳过处理: {document.metadata.get('doc_id', 'unknown')}")
                            continue
                            
                        document.page_content = document_text
                        
                        # 切割父文档
                        parent_documents = parent_splitter.split_documents([document])
                        processed_documents = []
                        
                        for parent_doc in parent_documents:
                            if not parent_doc.page_content.strip():
                                continue
                                
                            # 生成父文档ID和完整元数据
                            doc_id = str(uuid.uuid4())
                            parent_doc.metadata.update({
                                "doc_id": doc_id,
                                "is_parent": True,
                                "original_doc_id": document.metadata.get("doc_id")
                            })
                            
                            # 处理分隔符
                            content = self._clean_separators(parent_doc.page_content)
                            if not content:
                                continue
                                
                            parent_doc.page_content = content
                            
                            # 切割子文档
                            if child_splitter:
                                try:
                                    child_docs = self._split_child_documents(parent_doc, child_splitter)
                                    if child_docs:
                                        # 在父文档中保存子文档引用
                                        parent_doc.metadata["child_ids"] = [
                                            doc.metadata["doc_id"] for doc in child_docs
                                        ]
                                        parent_doc.metadata["child_count"] = len(child_docs)
                                        
                                        # 添加父子文档
                                        processed_documents.append(parent_doc)
                                        processed_documents.extend(child_docs)
                                        
                                        logger.info(f"处理父文档 {doc_id} 完成, 生成 {len(child_docs)} 个子文档")
                                except Exception as e:
                                    logger.error(f"处理子文档失败: {str(e)}")
                                    # 即使子文档处理失败，仍然保留父文档
                                    processed_documents.append(parent_doc)
                            else:
                                processed_documents.append(parent_doc)
                        
                        all_documents.extend(processed_documents)
                        logger.info(f"文档 {document.metadata.get('doc_id', 'unknown')} 处理完成, "
                                  f"生成 {len(processed_documents)} 个文档")
                        
                    except Exception as e:
                        logger.error(f"处理文档失败: {str(e)}")
                        continue
                        
            return all_documents
            
        except Exception as e:
            logger.error(f"文档转换失败: {str(e)}")
            raise ProcessingError(f"文档转换失败: {str(e)}")
    
    def _split_child_documents(
        self,
        parent_doc: Document,
        splitter: FixedRecursiveCharacterTextSplitter
    ) -> List[ChildDocument]:
        """切割子文档"""
        try:
            child_docs = []
            child_nodes = splitter.split_documents([parent_doc])
            
            for child_node in child_nodes:
                if not child_node.page_content.strip():
                    continue
                    
                # 生成子文档ID和完整元数据
                doc_id = str(uuid.uuid4())
                metadata = parent_doc.metadata.copy()
                metadata.update({
                    "doc_id": doc_id,
                    "parent_id": parent_doc.metadata["doc_id"],
                    "is_child": True,
                    "position": len(child_docs)  # 添加位置信息
                })
                
                # 处理分隔符
                content = self._clean_separators(child_node.page_content)
                if not content:
                    continue
                    
                # 创建子文档
                child_doc = ChildDocument(
                    page_content=content,
                    metadata=metadata,
                    parent_id=parent_doc.metadata["doc_id"],
                    parent_content=parent_doc.page_content
                )
                child_docs.append(child_doc)
                
            return child_docs
            
        except Exception as e:
            logger.error(f"切割子文档失败: {str(e)}")
            raise ProcessingError(f"切割子文档失败: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        try:
            if not text:
                return ""
            # 移除多余空白字符
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception as e:
            logger.error(f"清理文本失败: {str(e)}")
            return text.strip() if text else ""
    
    def _clean_separators(self, text: str) -> str:
        """处理分隔符"""
        try:
            if not text:
                return ""
            # 处理以分隔符开头的情况
            if text.startswith((".","。")):
                text = text[1:]
            return text.strip()
        except Exception as e:
            logger.error(f"处理分隔符失败: {str(e)}")
            return text.strip() if text else ""