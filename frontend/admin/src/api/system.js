import request from '@/utils/request'

// 获取系统监控指标
export function getSystemMetrics() {
  return request({
    url: '/admin/api/system/metrics',
    method: 'get'
  })
}

// 获取系统信息
export function getSystemInfo() {
  return request({
    url: '/admin/api/system/info',
    method: 'get'
  })
}

// 获取进程列表
export function getProcesses(params) {
  return request({
    url: '/admin/api/system/processes',
    method: 'get',
    params
  })
}

// 获取系统日志
export function getSystemLogs(params) {
  return request({
    url: '/admin/api/system/logs',
    method: 'get',
    params
  })
} 