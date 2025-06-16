import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import hashlib
from app.rag.models import Document

logger = logging.getLogger(__name__)

class DocumentStorage:
    def __init__(self, output_dir: str = None):
        """
        初始化文档存储服务
        
        Args:
            output_dir: 输出目录路径，默认为项目根目录下的data/results
        """
        if output_dir is None:
            # 使用项目根目录下的data/results目录
            project_root = Path(__file__).parent.parent.parent.parent
            self.output_dir = project_root / "data" / "results"
        else:
            self.output_dir = Path(output_dir)
            
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _generate_doc_hash(self, content: str) -> str:
        """生成文档内容的哈希值"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
        
    def save_split_results(self, parent_docs: List[Document], child_docs: List[Document], 
                          output_filename: str = "split_results.json", source_file: str = None) -> str:
        """
        将文档分割结果保存为JSON文件
        
        Args:
            parent_docs: 父文档列表
            child_docs: 子文档列表
            output_filename: 输出文件名
            source_file: 源文件路径
            
        Returns:
            str: 保存的文件路径
        """
        # 准备分割结果数据
        segments = []
        
        # 创建父文档ID到子文档的映射
        parent_children_map = {}
        for child in child_docs:
            parent_id = child.metadata.get("parent_id")
            if parent_id:
                if parent_id not in parent_children_map:
                    parent_children_map[parent_id] = []
                parent_children_map[parent_id].append(child)
        
        # 添加父文档及其子文档
        for i, doc in enumerate(parent_docs, 1):
            # 生成文档哈希值
            doc_hash = self._generate_doc_hash(doc.page_content)
            
            # 创建父文档段
            parent_segment = {
                "id": doc.id,
                "content": doc.page_content,
                "metadata": {
                    "source": doc.metadata.get("source", ""),
                    "type": "parent",
                    "index": i,
                    "original_doc_id": doc.id,
                    "doc_hash": doc_hash
                }
            }
            
            # 添加子文档
            children = []
            if doc.id in parent_children_map:
                for child in parent_children_map[doc.id]:
                    child_hash = self._generate_doc_hash(child.page_content)
                    child_segment = {
                        "id": child.id,
                        "content": child.page_content,
                        "metadata": {
                            "source": child.metadata.get("source", ""),
                            "type": "child",
                            "index": len(children) + 1,
                            "original_doc_id": child.id,
                            "doc_hash": child_hash
                        }
                    }
                    children.append(child_segment)
            
            parent_segment["children"] = children
            segments.append(parent_segment)
        
        # 构建完整的输出结构
        output_data = {
            "source_file": source_file or str(doc.metadata.get("source", "")),
            "split_mode": "parent_child",
            "metadata": {
                "total_segments": len(segments),
                "processed_at": datetime.now().isoformat()
            },
            "segments": segments
        }
        
        # 构建输出文件路径
        output_path = self.output_dir / output_filename
        
        # 保存为JSON文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"分割结果已保存到 {output_path}")
        return str(output_path) 