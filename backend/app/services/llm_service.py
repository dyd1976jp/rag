from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
import json
import httpx
from app.db.mongodb import mongodb
from app.models.llm import LLM
from app.schemas.llm import LLMCreate, LLMUpdate
from bson.objectid import ObjectId
import logging

# 配置日志
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.collection_name = "llms"

    async def create_llm(self, llm: LLMCreate) -> LLM:
        """创建新的LLM模型配置"""
        # 如果设置为默认，将其他默认模型设置为非默认
        if llm.default:
            await mongodb.db[self.collection_name].update_many(
                {"default": True},
                {"$set": {"default": False}}
            )

        llm_dict = llm.model_dump()
        llm_dict["created_at"] = datetime.now(timezone.utc)
        llm_dict["updated_at"] = datetime.now(timezone.utc)
        llm_dict["status"] = "active"
        
        result = await mongodb.db[self.collection_name].insert_one(llm_dict)
        return await self.get_llm(str(result.inserted_id))

    async def register_discovered_model(
        self,
        model_id: str,
        provider: str,
        name: str,
        api_url: str,
        description: Optional[str] = None,
        context_window: int = 8192,
        set_as_default: bool = False,
        max_output_tokens: int = 1000,
        temperature: float = 0.7,
        custom_options: Optional[Dict[str, Any]] = None
    ) -> LLM:
        """
        统一的模型注册方法，用于从发现的模型中注册到系统
        
        Args:
            model_id: 模型ID
            provider: 提供商名称
            name: 显示名称
            api_url: API URL
            description: 模型描述
            context_window: 上下文窗口大小
            set_as_default: 是否设置为默认模型
            max_output_tokens: 最大输出token数
            temperature: 温度参数
            custom_options: 自定义选项
            
        Returns:
            注册的模型
        """
        logger.info(f"注册模型: model_id={model_id}, provider={provider}, name={name}")
        
        # 自动识别模型类别
        model_category = "chat"  # 默认为聊天模型
        if "embedding" in model_id.lower():
            model_category = "embedding"
            logger.info(f"自动识别为embedding模型: {model_id}")
        
        # 准备默认值
        if not description:
            description = f"{provider}提供的{model_id}模型"
            
        timeout = 60 if provider.lower() == "local" else 30
        
        # 创建模型配置
        llm_create = LLMCreate(
            name=name,
            provider=provider,
            model_type=model_id,
            model_category=model_category,
            api_url=api_url,
            default=set_as_default,
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            description=description,
            timeout=timeout
        )
        
        # 添加自定义选项
        if custom_options:
            if not hasattr(llm_create, "config") or llm_create.config is None:
                llm_create.config = {}
            for key, value in custom_options.items():
                llm_create.config[key] = value
        
        # 调用创建服务
        result = await self.create_llm(llm_create)
        logger.info(f"模型注册成功: id={result.id}, name={result.name}, category={result.model_category}")
        return result

    async def get_llm(self, llm_id: str) -> Optional[LLM]:
        """获取LLM模型配置"""
        try:
            llm = await mongodb.db[self.collection_name].find_one({"_id": ObjectId(llm_id)})
            if llm:
                llm["id"] = str(llm["_id"])
                return LLM(**llm)
            return None
        except Exception:
            return None

    async def get_llms(self, skip: int = 0, limit: int = 100) -> List[LLM]:
        """获取所有LLM模型配置"""
        llms = []
        cursor = mongodb.db[self.collection_name].find().skip(skip).limit(limit)
        async for llm in cursor:
            llm["id"] = str(llm["_id"])
            llms.append(LLM(**llm))
        return llms

    async def update_llm(self, llm_id: str, llm_update: LLMUpdate) -> Optional[LLM]:
        """更新LLM模型配置"""
        llm = await self.get_llm(llm_id)
        if not llm:
            return None

        update_data = llm_update.model_dump(exclude_unset=True)
        
        # 如果要将此模型设置为默认，确保其他模型不是默认
        if update_data.get("default", False):
            await mongodb.db[self.collection_name].update_many(
                {"_id": {"$ne": ObjectId(llm_id)}, "default": True},
                {"$set": {"default": False}}
            )
        
        if update_data:
            update_data["updated_at"] = datetime.now(timezone.utc)
            await mongodb.db[self.collection_name].update_one(
                {"_id": ObjectId(llm_id)},
                {"$set": update_data}
            )
            
        return await self.get_llm(llm_id)

    async def delete_llm(self, llm_id: str) -> bool:
        """删除LLM模型配置"""
        result = await mongodb.db[self.collection_name].delete_one({"_id": ObjectId(llm_id)})
        return result.deleted_count > 0

    async def get_default_llm(self) -> Optional[LLM]:
        """获取默认LLM模型配置"""
        llm = await mongodb.db[self.collection_name].find_one({"default": True})
        if llm:
            llm["id"] = str(llm["_id"])
            return LLM(**llm)
        
        # 如果没有默认模型，返回第一个激活状态的模型
        llm = await mongodb.db[self.collection_name].find_one({"status": "active"})
        if llm:
            llm["id"] = str(llm["_id"])
            return LLM(**llm)
        
        return None

    async def test_llm(self, llm_id: str, prompt: str) -> Dict[str, Any]:
        """测试LLM模型"""
        llm = await self.get_llm(llm_id)
        if not llm:
            return {"error": "LLM模型不存在"}
        
        try:
            # 根据模型类别和提供商选择不同的测试方法
            logger.info(f"测试模型: id={llm_id}, type={llm.model_type}, category={llm.model_category}")
            
            if llm.model_category == "embedding":
                return await self._test_embedding_model(llm, prompt)
            elif llm.provider.lower() == "openai":
                return await self._test_openai_llm(llm, prompt)
            elif llm.provider.lower() == "local":
                return await self._test_local_llm(llm, prompt)
            else:
                return {"error": f"不支持的LLM提供商: {llm.provider}"}
        except Exception as e:
            logger.error(f"测试模型出错: {str(e)}")
            import traceback
            logger.debug(f"异常堆栈: {traceback.format_exc()}")
            return {"error": f"测试LLM时出错: {str(e)}"}
            
    async def _test_embedding_model(self, llm: LLM, prompt: str) -> Dict[str, Any]:
        """测试Embedding模型"""
        logger.info(f"测试Embedding模型: {llm.model_type}")
        headers = {"Content-Type": "application/json"}
        
        # 准备API URL - 根据不同的提供商调整URL
        api_url = llm.api_url
        if "lmstudio" in api_url.lower():
            # LM Studio中embedding模型的API端点
            api_url = api_url.replace("/chat/completions", "/embeddings")
            logger.info(f"LM Studio Embedding端点: {api_url}")
        elif "openai" in api_url.lower() and not api_url.endswith("/embeddings"):
            # OpenAI的embedding端点
            api_url = api_url.replace("/chat/completions", "/embeddings")
            logger.info(f"OpenAI Embedding端点: {api_url}")
            
        # 准备请求数据
        if llm.provider.lower() == "openai":
            payload = {
                "model": llm.model_type,
                "input": prompt,
                "encoding_format": "float"
            }
            headers["Authorization"] = f"Bearer {llm.api_key}"
        elif "ollama" in api_url.lower():
            payload = {
                "model": llm.model_type,
                "prompt": prompt
            }
        else:
            # 通用格式
            payload = {
                "model": llm.model_type,
                "input": prompt
            }
        
        # 添加自定义配置
        if llm.config:
            for key, value in llm.config.items():
                if key not in payload:
                    payload[key] = value
        
        # 发送请求
        logger.info(f"发送Embedding请求到: {api_url}")
        logger.debug(f"请求payload: {payload}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=llm.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API错误: {response.status_code}"
                logger.error(f"{error_msg}, 响应: {response.text}")
                return {
                    "error": error_msg,
                    "details": response.text
                }

    async def _test_openai_llm(self, llm: LLM, prompt: str) -> Dict[str, Any]:
        """测试OpenAI LLM"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm.api_key}"
        }
        
        payload = {
            "model": llm.model_type,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": llm.temperature,
            "max_tokens": llm.max_output_tokens,
            "top_p": llm.top_p,
            "frequency_penalty": llm.frequency_penalty,
            "presence_penalty": llm.presence_penalty
        }
        
        # 添加自定义配置
        if llm.config:
            for key, value in llm.config.items():
                if key not in payload:
                    payload[key] = value
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                llm.api_url,
                headers=headers,
                json=payload,
                timeout=llm.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"API错误: {response.status_code}",
                    "details": response.text
                }

    async def _test_local_llm(self, llm: LLM, prompt: str) -> Dict[str, Any]:
        """测试本地LLM（如LM Studio, Ollama等）"""
        logger.info(f"测试本地LLM模型: {llm.model_type}")
        headers = {"Content-Type": "application/json"}
        
        # 适配不同本地LLM的API格式
        if "lmstudio" in llm.api_url.lower():
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": llm.temperature,
                "max_tokens": llm.max_output_tokens,
                "top_p": llm.top_p
            }
        elif "ollama" in llm.api_url.lower():
            payload = {
                "model": llm.model_type,
                "prompt": prompt,
                "temperature": llm.temperature,
                "num_predict": llm.max_output_tokens,
                "top_p": llm.top_p
            }
        else:
            # 通用格式
            payload = {
                "model": llm.model_type,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": llm.temperature,
                "max_tokens": llm.max_output_tokens,
                "top_p": llm.top_p,
                "frequency_penalty": llm.frequency_penalty,
                "presence_penalty": llm.presence_penalty
            }
        
        # 添加自定义配置
        if llm.config:
            for key, value in llm.config.items():
                if key not in payload:
                    payload[key] = value
        
        async with httpx.AsyncClient() as client:
            logger.info(f"发送本地LLM请求到: {llm.api_url}")
            logger.debug(f"请求payload: {payload}")
            
            response = await client.post(
                llm.api_url,
                headers=headers,
                json=payload,
                timeout=llm.timeout  # 使用模型中配置的超时时间
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API错误: {response.status_code}"
                logger.error(f"{error_msg}, 响应: {response.text}")
                return {
                    "error": error_msg,
                    "details": response.text
                }
    
    async def set_default_llm(self, llm_id: str) -> Optional[LLM]:
        """设置默认LLM模型"""
        llm = await self.get_llm(llm_id)
        if not llm:
            return None
        
        # 将所有模型设置为非默认
        await mongodb.db[self.collection_name].update_many(
            {"default": True},
            {"$set": {"default": False}}
        )
        
        # 将当前模型设置为默认
        await mongodb.db[self.collection_name].update_one(
            {"_id": ObjectId(llm_id)},
            {"$set": {"default": True, "updated_at": datetime.now(timezone.utc)}}
        )
        
        return await self.get_llm(llm_id)
    
    async def get_providers(self) -> List[str]:
        """获取所有可用的LLM提供商"""
        # 预定义的提供商列表
        providers = ["OpenAI", "Anthropic", "Local", "Ollama", "Azure", "Google", "HuggingFace"]
        
        # 从数据库中获取已有的提供商
        db_providers = await mongodb.db[self.collection_name].distinct("provider")
        
        # 合并去重
        all_providers = list(set(providers + db_providers))
        all_providers.sort()
        
        return all_providers
    
    async def get_models_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """获取指定提供商下的所有模型类型"""
        # 每个提供商的预定义模型列表
        provider_models = {
            "openai": [
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "context_window": 16385},
                {"id": "gpt-4", "name": "GPT-4", "context_window": 8192},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "context_window": 128000},
                {"id": "gpt-4o", "name": "GPT-4o", "context_window": 128000}
            ],
            "anthropic": [
                {"id": "claude-3-opus", "name": "Claude 3 Opus", "context_window": 200000},
                {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet", "context_window": 180000},
                {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "context_window": 150000}
            ],
            "local": [
                {"id": "custom", "name": "自定义本地模型", "context_window": 4096}
            ],
            "ollama": [
                {"id": "llama3", "name": "Llama 3", "context_window": 8192},
                {"id": "mistral", "name": "Mistral", "context_window": 8192},
                {"id": "qwen", "name": "Qwen", "context_window": 8192},
                {"id": "gemma", "name": "Gemma", "context_window": 8192},
                {"id": "custom", "name": "自定义Ollama模型", "context_window": 4096}
            ],
            "azure": [
                {"id": "gpt-35-turbo", "name": "Azure GPT-3.5 Turbo", "context_window": 16385},
                {"id": "gpt-4", "name": "Azure GPT-4", "context_window": 8192}
            ],
            "google": [
                {"id": "gemini-pro", "name": "Gemini Pro", "context_window": 32768},
                {"id": "gemini-ultra", "name": "Gemini Ultra", "context_window": 32768}
            ],
            "huggingface": [
                {"id": "custom", "name": "自定义HuggingFace模型", "context_window": 4096}
            ]
        }
        
        # 不区分大小写查找
        provider_lower = provider.lower()
        if provider_lower in provider_models:
            return provider_models[provider_lower]
        
        # 如果没有预定义模型，查询数据库中是否有使用该提供商的模型
        models = []
        cursor = mongodb.db[self.collection_name].find(
            {"provider": {"$regex": f"^{provider}$", "$options": "i"}}
        )
        async for llm in cursor:
            models.append({
                "id": llm["model_type"],
                "name": llm["model_type"],
                "context_window": llm.get("context_window", 4096)
            })
        
        # 去重
        unique_models = []
        model_ids = set()
        for model in models:
            if model["id"] not in model_ids:
                model_ids.add(model["id"])
                unique_models.append(model)
        
        return unique_models if unique_models else [{"id": "custom", "name": "自定义模型", "context_window": 4096}]
    
    async def discover_local_models(self, provider: str, url: str) -> List[Dict[str, Any]]:
        """发现本地服务（如LM Studio）中的模型"""
        try:
            print("\n" + "-"*50)
            print(f"LLMService.discover_local_models被调用")
            print(f"参数 - 提供商: {provider}, URL: {url}")
            
            # 验证URL格式
            if not url:
                print("错误: URL不能为空")
                return [{"error": "URL不能为空"}]
                
            if not url.startswith("http"):
                print(f"警告: URL格式不正确，正在添加http://前缀: {url}")
                url = "http://" + url
                print(f"修正后的URL: {url}")
            
            if provider.lower() == "lmstudio":
                # 确保URL格式正确
                base_url = url.rstrip("/")
                models_url = f"{base_url}/v1/models"  # 移除末尾的斜杠
                
                print(f"请求LM Studio API: {models_url}")
                async with httpx.AsyncClient() as client:
                    try:
                        print(f"发送GET请求到: {models_url}")
                        response = await client.get(models_url, timeout=10.0)
                        print(f"LM Studio API响应状态码: {response.status_code}")
                        
                        if response.status_code == 200:
                            response_json = response.json()
                            print(f"LM Studio API响应头部: {response.headers}")
                            print(f"LM Studio API响应内容摘要: {str(response_json)[:200]}...")
                            models_data = response_json.get("data", [])
                            print(f"解析到的模型数据数量: {len(models_data)}")
                            
                            # 获取已注册模型列表用于对比
                            try:
                                registered_models = await self.get_llms()
                                print(f"获取到已注册模型数量: {len(registered_models)}")
                                registered_model_types = {model.model_type for model in registered_models}
                                print(f"已注册模型类型: {registered_model_types}")
                            except Exception as e:
                                print(f"获取已注册模型时出错: {str(e)}")
                                registered_model_types = set()
                            
                            # 转换为标准格式
                            discovered_models = []
                            for model in models_data:
                                model_id = model["id"]
                                print(f"处理模型: {model_id}")
                                
                                # 识别模型类别
                                model_category = "chat"  # 默认为聊天模型
                                if "embedding" in model_id.lower():
                                    model_category = "embedding"
                                    print(f"识别到embedding模型: {model_id}")
                                
                                # 根据模型类别确定正确的API URL
                                api_url = f"{base_url}/v1/chat/completions"
                                if model_category == "embedding":
                                    api_url = f"{base_url}/v1/embeddings"
                                    print(f"为embedding模型设置端点: {api_url}")
                                
                                discovered_models.append({
                                    "id": model_id,
                                    "name": model_id,
                                    "provider": "Local",
                                    "model_category": model_category,
                                    "is_registered": model_id in registered_model_types,
                                    "api_url": api_url,
                                    "context_window": 8192,  # 默认值，实际值需要从模型信息中获取
                                    "description": f"LM Studio中的{model_id}模型"
                                })
                            
                            print(f"发现的模型总数: {len(discovered_models)}")
                            print("-"*50 + "\n")
                            return discovered_models
                        else:
                            error_msg = f"无法连接到LM Studio: HTTP {response.status_code}"
                            print(f"错误: {error_msg}")
                            try:
                                print(f"响应内容: {response.text}")
                            except:
                                print("无法获取响应内容")
                            print("-"*50 + "\n")
                            return [{"error": error_msg, "details": response.text}]
                    except Exception as request_error:
                        error_msg = f"请求LM Studio API时出错: {str(request_error)}"
                        print(f"错误: {error_msg}")
                        import traceback
                        print(f"异常堆栈: {traceback.format_exc()}")
                        print("-"*50 + "\n")
                        return [{"error": error_msg}]
            
            elif provider.lower() == "ollama":
                # Ollama API的模型列表端点
                models_url = f"{url.rstrip('/')}/api/tags"
                
                print(f"请求Ollama API: {models_url}")
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(models_url, timeout=10.0)
                        print(f"Ollama API响应状态码: {response.status_code}")
                        
                        if response.status_code == 200:
                            response_json = response.json()
                            print(f"Ollama API响应内容: {response_json}")
                            models_data = response_json.get("models", [])
                            print(f"解析到的模型数据: {models_data}")
                            
                            # 获取已注册模型列表用于对比
                            try:
                                registered_models = await self.get_llms()
                                print(f"获取到已注册模型数量: {len(registered_models)}")
                                registered_model_types = {model.model_type for model in registered_models}
                                print(f"已注册模型类型: {registered_model_types}")
                            except Exception as e:
                                print(f"获取已注册模型时出错: {str(e)}")
                                registered_model_types = set()
                            
                            # 转换为标准格式
                            discovered_models = []
                            for model in models_data:
                                model_name = model.get("name", "")
                                print(f"处理模型: {model_name}")
                                
                                # 识别模型类别
                                model_category = "chat"  # 默认为聊天模型
                                if "embedding" in model_name.lower():
                                    model_category = "embedding"
                                    print(f"识别到embedding模型: {model_name}")
                                
                                # 根据模型类别确定正确的API URL
                                api_url = f"{url.rstrip('/')}/api/generate"
                                if model_category == "embedding":
                                    # Ollama可能有不同的embedding端点，需要根据实际情况调整
                                    api_url = f"{url.rstrip('/')}/api/embeddings"
                                    print(f"为embedding模型设置端点: {api_url}")
                                
                                discovered_models.append({
                                    "id": model_name,
                                    "name": model_name,
                                    "provider": "Ollama",
                                    "model_category": model_category,
                                    "is_registered": model_name in registered_model_types,
                                    "api_url": api_url,
                                    "context_window": model.get("details", {}).get("context_length", 4096),
                                    "description": f"Ollama中的{model_name}模型"
                                })
                            
                            print(f"发现的模型总数: {len(discovered_models)}")
                            return discovered_models
                        else:
                            error_msg = f"无法连接到Ollama: HTTP {response.status_code}"
                            print(f"错误: {error_msg}")
                            try:
                                print(f"响应内容: {response.text}")
                            except:
                                print("无法获取响应内容")
                            return [{"error": error_msg, "details": response.text}]
                    except Exception as request_error:
                        error_msg = f"请求Ollama API时出错: {str(request_error)}"
                        print(f"错误: {error_msg}")
                        return [{"error": error_msg}]
            
            provider_error = f"不支持的提供商: {provider}"
            print(f"错误: {provider_error}")
            return [{"error": provider_error}]
            
        except Exception as e:
            error_msg = f"发现模型时出错: {str(e)}"
            print(f"错误: {error_msg}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            return [{"error": error_msg}]

llm_service = LLMService() 