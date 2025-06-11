import { defineStore } from 'pinia'
import { login, getUserInfo } from '@/api/auth'
import Cookies from 'js-cookie'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: Cookies.get('admin_token') || '',
    username: '',
    email: '',
    isActive: false
  }),
  
  getters: {
    isLoggedIn: (state) => !!state.token
  },
  
  actions: {
    // 登录
    async loginAction(username, password) {
      try {
        const response = await login(username, password)
        const { access_token, token_type } = response
        
        // 保存令牌
        this.token = access_token
        
        // 将令牌存储在Cookie中，设置过期时间为12小时
        Cookies.set('admin_token', access_token, { expires: 0.5 })
        
        // 获取用户信息
        await this.getUserInfoAction()
        
        return Promise.resolve()
      } catch (error) {
        return Promise.reject(error)
      }
    },
    
    // 获取用户信息
    async getUserInfoAction() {
      try {
        const data = await getUserInfo()
        this.username = data.username
        this.email = data.email
        this.isActive = data.is_active
        return Promise.resolve(data)
      } catch (error) {
        return Promise.reject(error)
      }
    },
    
    // 登出
    logoutAction() {
      // 清除状态
      this.token = ''
      this.username = ''
      this.email = ''
      this.isActive = false
      
      // 删除Cookie
      Cookies.remove('admin_token')
    }
  }
}) 