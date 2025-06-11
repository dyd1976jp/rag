import axios, { AxiosRequestConfig } from 'axios';

// 创建axios实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1', // 从环境变量获取基础URL
  timeout: 15000 // 请求超时时间
});

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    console.log('Response interceptor:', {
      url: response.config.url,
      status: response.status,
      data: response.data
    });
    return response;
  },
  (error) => {
    console.error('Response error interceptor:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    
    // 处理401未授权错误
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/auth';
      return Promise.reject(new Error('未授权，请重新登录'));
    }
    
    // 处理其他错误
    const message = error.response?.data?.message || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

export default request; 