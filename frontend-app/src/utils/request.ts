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
    // 添加详细日志
    console.log('Request config:', {
      url: config.url,
      method: config.method,
      headers: config.headers,
      data: config.data
    });
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
      data: response.data,
      headers: response.headers
    });
    
    // 检查是否是重定向响应
    if (response.status === 307 || response.status === 308) {
      console.log('处理重定向响应:', response.headers.location);
      // 创建新的请求配置
      const redirectConfig = {
        ...response.config,
        url: response.headers.location
      };
      // 重新发送请求
      return request(redirectConfig);
    }
    
    return response;
  },
  (error) => {
    console.error('Response error interceptor:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
      headers: error.response?.headers
    });
    
    // 处理401未授权错误
    if (error.response && error.response.status === 401) {
      console.log('检测到未授权错误，清除token并重定向到登录页面');
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