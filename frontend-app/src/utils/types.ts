/**
 * 通用类型定义
 */

// 用户类型
export interface User {
  id: string;
  username: string;
  email: string;
  is_superuser: boolean;
  created_at: string;
}

// 聊天消息类型
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

// 文档类型
export interface Document {
  id: string;
  file_name: string;
  segments_count: number;
  created_at: Date;
  status: 'ready' | 'processing' | 'error';
}

// 预览段落类型
export interface PreviewSegment {
  id: number;
  content: string;
  start: number;
  end: number;
  length: number;
}

// 模型类型
export interface Model {
  id: string;
  name: string;
  provider: string;
  model_type: string;
  api_url: string;
  api_key?: string;
  description: string;
  context_window: number;
  max_output_tokens: number;
  temperature: number;
  default: boolean;
  status: 'active' | 'inactive';
  config?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// 发现的模型类型
export interface DiscoveredModel {
  id: string;
  name: string;
  provider: string;
  is_registered: boolean;
  api_url: string;
  context_window: number;
  description: string;
}

// API错误类型
export interface ApiError {
  status: number;
  detail: string;
}

// API响应类型
export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
} 