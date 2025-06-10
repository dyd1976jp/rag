<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="login-header">
          <h2>RAG系统管理后台</h2>
        </div>
      </template>
      
      <el-form 
        :model="loginForm" 
        :rules="loginRules" 
        ref="loginFormRef" 
        label-position="top" 
        @keyup.enter="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入用户名"></el-input>
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码"
            show-password
          ></el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            :loading="loading" 
            style="width: 100%"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-tips">
        <p>默认用户名: admin</p>
        <p>默认密码: adminpassword</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

// 获取路由信息
const router = useRouter()
const route = useRoute()

// 用户store
const userStore = useUserStore()

// 表单引用
const loginFormRef = ref(null)

// 登录加载状态
const loading = ref(false)

// 登录表单数据
const loginForm = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 处理登录
const handleLogin = () => {
  loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    
    try {
      // 调用登录action
      await userStore.loginAction(loginForm.username, loginForm.password)
      
      // 登录成功提示
      ElMessage({
        message: '登录成功',
        type: 'success'
      })
      
      // 重定向到目标页面或默认页面
      const redirectPath = route.query.redirect || '/'
      router.push(redirectPath)
    } catch (error) {
      console.error('登录失败:', error)
      
      // 登录失败提示
      ElMessage({
        message: '登录失败，请检查用户名和密码',
        type: 'error'
      })
    } finally {
      loading.value = false
    }
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}

.login-card {
  width: 400px;
  max-width: 100%;
  
  .login-header {
    text-align: center;
    
    h2 {
      margin: 0;
      font-weight: 500;
      color: #303133;
    }
  }
  
  .login-tips {
    margin-top: 20px;
    font-size: 12px;
    line-height: 1.5;
    color: #909399;
    text-align: center;
  }
}
</style> 