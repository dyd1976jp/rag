import request from '@/utils/request'

// 获取所有集合
export function getCollections() {
  return request({
    url: '/admin/api/mongodb/collections',
    method: 'get'
  })
}

// 获取集合数据
export function getCollectionData(collectionName, params) {
  return request({
    url: `/admin/api/mongodb/collections/${collectionName}`,
    method: 'get',
    params
  })
}

// 插入文档
export function insertDocument(collectionName, document) {
  return request({
    url: `/admin/api/mongodb/collections/${collectionName}/documents`,
    method: 'post',
    data: {
      document
    }
  })
}

// 更新文档
export function updateDocuments(collectionName, query, update) {
  return request({
    url: `/admin/api/mongodb/collections/${collectionName}/documents`,
    method: 'put',
    data: {
      query,
      update
    }
  })
}

// 删除文档
export function deleteDocuments(collectionName, query) {
  return request({
    url: `/admin/api/mongodb/collections/${collectionName}/documents`,
    method: 'delete',
    data: {
      query
    }
  })
} 