import request from '../utils/request';
import { DocumentCollection, DocumentCollectionCreate, DocumentCollectionUpdate } from '../types/documentCollection';

// 后端API响应的数据结构
interface CollectionResponse {
  success: boolean;
  message: string;
  data: {
    collections: DocumentCollection[];
  }
}

// 创建文档集
export const createCollection = (data: DocumentCollectionCreate) => {
  return request({
    url: '/rag/collections',
    method: 'post',
    data
  });
};

// 获取用户的所有文档集
export const getCollections = async () => {
  try {
    // 检查token是否存在
    const token = localStorage.getItem('token');
    if (!token) {
      console.error('Token不存在，用户可能未登录');
      throw new Error('请先登录');
    }

    console.log('开始获取文档集列表...');
    const response = await request<CollectionResponse>({
      url: '/rag/collections/',  // 添加末尾的斜杠以避免重定向
      method: 'get'
    });
    
    console.log('文档集API响应:', {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
      data: response.data
    });

    // 验证响应数据结构
    if (!response.data || !response.data.success) {
      console.error('API响应格式不正确:', response.data);
      throw new Error(response.data?.message || '获取文档集失败');
    }

    return response;
  } catch (error: any) {
    console.error('获取文档集列表失败:', {
      error,
      message: error.message,
      response: error.response?.data
    });
    throw error;
  }
};

// 获取文档集详情
export const getCollection = (collectionId: string) => {
  return request({
    url: `/rag/collections/${collectionId}`,
    method: 'get'
  });
};

// 更新文档集
export const updateCollection = (collectionId: string, data: DocumentCollectionUpdate) => {
  return request({
    url: `/rag/collections/${collectionId}`,
    method: 'put',
    data
  });
};

// 删除文档集
export const deleteCollection = (collectionId: string) => {
  return request({
    url: `/rag/collections/${collectionId}`,
    method: 'delete'
  });
};

// 将文档添加到文档集
export const addDocumentToCollection = (collectionId: string, documentId: string) => {
  return request({
    url: `/rag/collections/${collectionId}/documents/${documentId}`,
    method: 'post'
  });
};

// 从文档集中移除文档
export const removeDocumentFromCollection = (collectionId: string, documentId: string) => {
  return request({
    url: `/rag/collections/${collectionId}/documents/${documentId}`,
    method: 'delete'
  });
};

// 获取文档集中的所有文档
export const getCollectionDocuments = (collectionId: string) => {
  return request({
    url: `/rag/collections/${collectionId}/documents`,
    method: 'get'
  });
};

// 后端 API 响应的数据类型
interface DocumentSlicePreviewResponse {
  success: boolean;
  message: string;
  parentContent: string;
  childrenContent: string[];
  segments: Array<{
    id: number;
    content: string;
    start: number;
    end: number;
    length: number;
  }>;
  total_segments: number;
}

// 前端使用的数据类型
export interface DocumentSlicePreview {
  parentContent: string;
  childrenContent: string[];
}

export interface DocumentSliceError {
  message: string;
  code: string;
}

export const getDocumentSlicePreview = async (documentId: string, segmentId: number): Promise<DocumentSlicePreviewResponse> => {
  if (!documentId) {
    throw new Error('文档ID不能为空');
  }

  try {
    const response = await request<DocumentSlicePreviewResponse>({
      url: `/rag/collections/${documentId}/preview/${segmentId}`,
      method: 'get'
    });

    if (!response.data) {
      throw new Error('获取切片预览失败');
    }

    return response.data;
  } catch (error: any) {
    const errorMessage = error.response?.data?.message || error.message || '获取切片预览失败';
    throw new Error(errorMessage);
  }
};

// 定义切割参数接口
export interface SplitterParams {
  chunk_size: number;
  chunk_overlap: number;
  min_chunk_size: number;
  split_by_paragraph: boolean;
  paragraph_separator: string;
  split_by_sentence: boolean;
}

// 获取文档切割参数
export const getDocumentSplitterParams = async (documentId: string): Promise<SplitterParams> => {
  if (!documentId) {
    throw new Error('文档ID不能为空');
  }

  try {
    const response = await request<SplitterParams>({
      url: `/rag/collections/${documentId}/splitter-params`,
      method: 'get'
    });

    if (!response.data) {
      throw new Error('获取切割参数失败');
    }

    return response.data;
  } catch (error: any) {
    const errorMessage = error.response?.data?.message || error.message || '获取切割参数失败';
    throw new Error(errorMessage);
  }
};

// 完整文档预览API响应的数据类型
export interface CompleteDocumentPreviewResponse {
  success: boolean;
  message?: string;
  preview_mode: boolean;
  doc_id: string;
  total_segments: number;
  segments: Array<{
    id: number;
    content: string;
    start: number;
    end: number;
    length: number;
  }>;
  parentContent: string;
  childrenContent: string[];
}

// 完整文档预览API调用函数
export const getCompleteDocumentPreview = async (
  file: File,
  chunkSize: number = 512,
  chunkOverlap: number = 50,
  splitByParagraph: boolean = true,
  splitBySentence: boolean = true
): Promise<CompleteDocumentPreviewResponse> => {
  if (!file) {
    throw new Error('文件不能为空');
  }

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('parent_chunk_size', chunkSize.toString());
    formData.append('parent_chunk_overlap', chunkOverlap.toString());
    formData.append('parent_separator', '\n\n');
    formData.append('child_chunk_size', Math.floor(chunkSize / 2).toString());
    formData.append('child_chunk_overlap', Math.floor(chunkOverlap / 4).toString());
    formData.append('child_separator', '\n');
    formData.append('preview_only', 'true'); // 设置为预览模式

    const response = await request<CompleteDocumentPreviewResponse>({
      url: '/rag/documents/upload',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    if (!response.data) {
      throw new Error('获取完整文档预览失败');
    }

    if (!response.data.success) {
      throw new Error(response.data.message || '获取完整文档预览失败');
    }

    return response.data;
  } catch (error: any) {
    const errorMessage = error.response?.data?.message || error.message || '获取完整文档预览失败';
    throw new Error(errorMessage);
  }
};
