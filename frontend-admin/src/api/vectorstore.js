import request from '@/utils/request'

// 获取所有向量集合
export function getVectorCollections() {
  return request({
    url: '/admin/api/vector/collections',
    method: 'get'
  })
}

// 获取向量集合统计信息
export function getCollectionStats(collectionName) {
  return request({
    url: `/admin/api/vector/collections/${collectionName}/stats`,
    method: 'get'
  })
}

// 获取向量集合样本数据
export function getCollectionSample(collectionName, limit = 10) {
  return request({
    url: `/admin/api/vector/collections/${collectionName}/sample`,
    method: 'get',
    params: { limit }
  })
}

// 刷新向量集合
export function flushCollection(collectionName) {
  return request({
    url: `/admin/api/vector/collections/${collectionName}/flush`,
    method: 'post'
  })
}

// 清空向量集合
export function purgeCollection(collectionName) {
  return request({
    url: `/admin/api/vector/collections/${collectionName}/purge`,
    method: 'delete'
  })
} 