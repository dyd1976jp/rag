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
    const response = await request<CollectionResponse>({
      url: '/rag/collections',
      method: 'get'
    });
    console.log('API Response:', response);
    console.log('Response data structure:', JSON.stringify(response.data, null, 2));
    return response;
  } catch (error) {
    console.error('getCollections API error:', error);
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
      url: `/api/v1/rag/collections/documents/${documentId}/slices/${segmentId}/preview`,
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
      url: `/api/v1/rag/collections/documents/${documentId}/splitter-params`,
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
