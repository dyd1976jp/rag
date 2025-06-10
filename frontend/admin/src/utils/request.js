import axios from 'axios'
import { ElMessage } from 'element-plus'
import Cookies from 'js-cookie'
import router from '@/router'

// 创建axios实例
const service = axios.create({
  baseURL: '',  // API的基础URL，会自动添加到请求URL前面
  timeout: 15000  // 请求超时时间
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 在发送请求之前做些什么
    const token = Cookies.get('admin_token')
    if (token) {
      // 让每个请求携带token
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    // 对请求错误做些什么
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 2xx 范围内的状态码都会触发该函数
    return response.data
  },
  error => {
    // 超出 2xx 范围的状态码都会触发该函数
    let message = '未知错误'
    
    if (error.response) {
      // 服务器返回了错误响应
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          message = data.detail || '请求参数错误'
          break
        case 401:
          message = '未授权，请重新登录'
          // 清除令牌并跳转到登录页
          Cookies.remove('admin_token')
          router.push('/login')
          break
        case 403:
          message = '拒绝访问'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 500:
          message = '服务器内部错误'
          break
        default:
          message = `请求错误: ${status}`
      }
      
      // 如果服务器返回了详细错误信息，优先使用
      if (data && data.detail) {
        message = data.detail
      }
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      message = '服务器无响应'
    } else {
      // 请求配置有误
      message = error.message
    }
    
    // 使用Element Plus的消息提示
    ElMessage({
      message,
      type: 'error',
      duration: 5000
    })
    
    return Promise.reject(error)
  }
)

export default service 