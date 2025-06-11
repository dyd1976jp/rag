import request from '@/utils/request'

// 获取RAG服务状态
export function getRAGStatus() {
  return request({
    url: '/api/v1/rag/status',
    method: 'get'
  })
}

// 获取文档列表
export function getDocuments() {
  return request({
    url: '/api/v1/rag/documents',
    method: 'get'
  })
}

// 获取文档状态
export function getDocumentStatus(docId) {
  return request({
    url: `/api/v1/rag/documents/${docId}`,
    method: 'get'
  })
}

// 删除文档
export function deleteDocument(docId) {
  return request({
    url: `/api/v1/rag/documents/${docId}`,
    method: 'delete'
  })
}

// 搜索文档
export function searchDocuments(data) {
  return request({
    url: '/api/v1/rag/documents/search',
    method: 'post',
    data
  })
}

// 预览文档切割
export function previewDocumentSplit(data) {
  return request({
    url: '/api/v1/rag/documents/preview-split',
    method: 'post',
    data
  })
} 