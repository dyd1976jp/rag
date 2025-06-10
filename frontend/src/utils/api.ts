/**
 * API工具函数
 * 用于处理与后端API的交互
 */

// API基础URL
const API_BASE_URL = '/api/v1';

// 通用请求方法
const fetchAPI = async (
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body?: any
) => {
  const token = localStorage.getItem('token');
  
  if (!token) {
    throw new Error('未授权，请先登录');
  }
  
  const headers: HeadersInit = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
  
  const options: RequestInit = {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  };
  
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    
    if (!response.ok) {
      // 尝试解析错误信息
      try {
        const errorData = await response.json();
        throw new Error(errorData.detail || `请求失败 (${response.status})`);
      } catch (e) {
        throw new Error(`请求失败 (${response.status})`);
      }
    }
    
    // 204 No Content 不返回任何内容
    if (response.status === 204) {
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API错误 (${endpoint}):`, error);
    throw error;
  }
};

// LLM模型API
export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  model_type: string;
  model_category?: string;
  api_url: string;
  api_key?: string;
  description: string;
  context_window: number;
  max_output_tokens: number;
  temperature: number;
  default: boolean;
  status: string;
  config?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateLLMModel {
  name: string;
  provider: string;
  model_type: string;
  model_category?: string;
  api_url: string;
  api_key?: string;
  description?: string;
  context_window?: number;
  max_output_tokens?: number;
  temperature?: number;
  default?: boolean;
  config?: Record<string, any>;
}

export interface UpdateLLMModel {
  name?: string;
  provider?: string;
  model_type?: string;
  model_category?: string;
  api_url?: string;
  api_key?: string;
  description?: string;
  context_window?: number;
  max_output_tokens?: number;
  temperature?: number;
  default?: boolean;
  config?: Record<string, any>;
}

export interface DiscoveredModel {
  id: string;
  name: string;
  provider: string;
  model_category?: string;
  is_registered: boolean;
  api_url: string;
  context_window: number;
  description: string;
}

export interface RegisterDiscoveredModel {
  llm_model_id: string;
  provider: string;
  name: string;
  api_url: string;
  description?: string;
  context_window?: number;
  set_as_default?: boolean;
  max_output_tokens?: number;
  temperature?: number;
  custom_options?: Record<string, any>;
}

// 获取所有LLM模型
export const getLLMModels = async (): Promise<LLMModel[]> => {
  return fetchAPI('/llm');
};

// 获取单个LLM模型
export const getLLMModel = async (id: string): Promise<LLMModel> => {
  return fetchAPI(`/llm/${id}`);
};

// 创建LLM模型
export const createLLMModel = async (model: CreateLLMModel): Promise<LLMModel> => {
  return fetchAPI('/llm', 'POST', model);
};

// 更新LLM模型
export const updateLLMModel = async (id: string, model: UpdateLLMModel): Promise<LLMModel> => {
  return fetchAPI(`/llm/${id}`, 'PUT', model);
};

// 删除LLM模型
export const deleteLLMModel = async (id: string): Promise<void> => {
  return fetchAPI(`/llm/${id}`, 'DELETE');
};

// 设置默认LLM模型
export const setDefaultLLMModel = async (id: string): Promise<LLMModel> => {
  return fetchAPI(`/llm/set-default/${id}`, 'POST');
};

// 发现本地模型
export const discoverModels = async (
  provider: string,
  url: string
): Promise<DiscoveredModel[]> => {
  return fetchAPI(`/discover/?provider=${encodeURIComponent(provider)}&url=${encodeURIComponent(url)}`);
};

// 注册发现的模型
export const registerDiscoveredModel = async (
  model: RegisterDiscoveredModel
): Promise<LLMModel> => {
  return fetchAPI('/discover/register', 'POST', model);
};

// 测试LLM模型
export const testLLMModel = async (
  llm_id: string,
  prompt: string
): Promise<any> => {
  return fetchAPI('/llm/test', 'POST', { llm_id, prompt });
};

// 获取所有可用的LLM提供商
export const getLLMProviders = async (): Promise<string[]> => {
  return fetchAPI('/llm/providers/list');
};

// 导出默认API对象
export default {
  getLLMModels,
  getLLMModel,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
  setDefaultLLMModel,
  discoverModels,
  registerDiscoveredModel,
  testLLMModel,
  getLLMProviders
}; 