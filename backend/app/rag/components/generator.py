"""
答案生成器组件

实现基于LLM的答案生成功能。
实现IGenerator接口，提供统一的答案生成功能。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import openai
from openai import AsyncOpenAI

from app.rag.interfaces import BaseGenerator, RetrievalResult, GenerationResult
from app.core.config import settings

logger = logging.getLogger(__name__)

class Generator(BaseGenerator):
    """答案生成器实现"""
    
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        max_retries: int = 3
    ):
        """
        初始化答案生成器
        
        Args:
            model_name: LLM模型名称
            api_key: API密钥
            api_base: API基础URL
            temperature: 生成温度
            max_tokens: 最大token数
            max_retries: 最大重试次数
        """
        self.model_name = model_name
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = api_base or settings.EMBEDDING_API_BASE
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        
        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
        # 默认系统提示词
        self.system_prompt = """你是一个专业的AI助手，专门基于提供的文档内容回答用户问题。

请遵循以下规则：
1. 仅基于提供的文档内容回答问题
2. 如果文档中没有相关信息，请明确说明
3. 回答要准确、简洁、有条理
4. 如果可能，请引用具体的文档片段
5. 保持客观中立的语调"""
    
    async def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        **kwargs
    ) -> GenerationResult:
        """
        基于查询和上下文生成答案
        
        Args:
            query: 用户查询
            context: 检索到的上下文
            **kwargs: 其他生成参数
            
        Returns:
            GenerationResult: 生成结果
        """
        if not query.strip():
            return GenerationResult(
                answer="请提供有效的问题。",
                sources=[],
                metadata={"error": "empty_query"}
            )
        
        # 构建上下文
        context_text = self._build_context(context)
        
        # 构建提示词
        prompt = self._build_prompt(query, context_text)
        
        # 生成答案
        try:
            answer = await self._call_llm(prompt, **kwargs)
            
            return GenerationResult(
                answer=answer,
                sources=context,
                metadata={
                    "model": self.model_name,
                    "context_length": len(context_text),
                    "sources_count": len(context),
                    "query": query
                }
            )
            
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return GenerationResult(
                answer="抱歉，生成答案时出现错误，请稍后重试。",
                sources=context,
                metadata={"error": str(e)}
            )
    
    def configure(self, **kwargs) -> None:
        """
        配置生成器参数
        
        Args:
            **kwargs: 配置参数
        """
        if 'temperature' in kwargs:
            self.temperature = max(0.0, min(2.0, kwargs['temperature']))
        if 'max_tokens' in kwargs:
            self.max_tokens = max(1, kwargs['max_tokens'])
        if 'system_prompt' in kwargs:
            self.system_prompt = kwargs['system_prompt']
        if 'max_retries' in kwargs:
            self.max_retries = max(0, kwargs['max_retries'])
    
    def _build_context(self, context: List[RetrievalResult]) -> str:
        """
        构建上下文文本
        
        Args:
            context: 检索结果列表
            
        Returns:
            str: 构建的上下文文本
        """
        if not context:
            return "没有找到相关的文档内容。"
        
        context_parts = []
        for i, result in enumerate(context, 1):
            # 添加文档片段
            context_parts.append(f"文档片段 {i}:")
            context_parts.append(f"内容: {result.content}")
            
            # 添加元数据信息
            if result.metadata:
                file_name = result.metadata.get("file_name", "未知文件")
                context_parts.append(f"来源: {file_name}")
            
            context_parts.append("")  # 空行分隔
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """
        构建完整的提示词
        
        Args:
            query: 用户查询
            context: 上下文文本
            
        Returns:
            str: 完整的提示词
        """
        prompt = f"""基于以下文档内容，回答用户的问题。

文档内容：
{context}

用户问题：{query}

请基于上述文档内容回答问题。如果文档中没有相关信息，请明确说明。"""
        
        return prompt
    
    async def _call_llm(self, prompt: str, **kwargs) -> str:
        """
        调用LLM生成答案
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            str: 生成的答案
        """
        # 合并参数
        generation_params = {
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    **generation_params
                )
                
                answer = response.choices[0].message.content
                logger.debug(f"成功生成答案，长度: {len(answer)} 字符")
                return answer
                
            except openai.RateLimitError as e:
                wait_time = 2 ** attempt
                logger.warning(f"API限流，等待 {wait_time} 秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)
                
            except openai.APIError as e:
                logger.error(f"API错误: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception(f"LLM调用失败，已重试 {self.max_retries} 次")
    
    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        生成文本摘要
        
        Args:
            text: 要摘要的文本
            max_length: 最大摘要长度
            
        Returns:
            str: 生成的摘要
        """
        prompt = f"""请为以下文本生成一个简洁的摘要，长度不超过{max_length}字符：

{text}

摘要："""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的文本摘要助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_length
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_retries": self.max_retries,
            "api_base": self.api_base
        }
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 服务是否可用
        """
        try:
            test_result = await self.generate(
                query="测试问题",
                context=[RetrievalResult(content="测试内容", score=1.0)]
            )
            return bool(test_result.answer)
        except Exception as e:
            logger.error(f"生成服务健康检查失败: {e}")
            return False
