<template>
  <div class="admin-container">
    <!-- 头部 -->
    <header class="admin-header">
      <div class="logo">
        <h1>RAG管理系统</h1>
      </div>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <span class="el-dropdown-link">
            <el-avatar :size="32" icon="el-icon-user-solid"></el-avatar>
            <span class="username">{{ username }}</span>
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>
    
    <!-- 内容区 -->
    <div class="admin-content">
      <!-- 侧边栏 -->
      <aside class="admin-sidebar">
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          :router="true"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Monitor /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          
          <el-menu-item index="/rag">
            <el-icon><DataAnalysis /></el-icon>
            <span>RAG管理</span>
          </el-menu-item>
          
          <el-menu-item index="/mongodb">
            <el-icon><Files /></el-icon>
            <span>MongoDB管理</span>
          </el-menu-item>
          
          <el-menu-item index="/vectorstore">
            <el-icon><Collection /></el-icon>
            <span>向量存储管理</span>
          </el-menu-item>
          
          <el-menu-item index="/system">
            <el-icon><Setting /></el-icon>
            <span>系统监控</span>
          </el-menu-item>
        </el-menu>
      </aside>
      
      <!-- 主内容 -->
      <main class="admin-main">
        <router-view />
      </main>
    </div>
    
    <!-- 页脚 -->
    <footer class="admin-footer">
      <p>RAG系统管理后台 &copy; {{ currentYear }}</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowDown, Monitor, Files, Collection, Setting, DataAnalysis } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

// 获取用户信息
const userStore = useUserStore()
const username = computed(() => userStore.username || '管理员')

// 路由信息
const router = useRouter()
const route = useRoute()

// 当前年份
const currentYear = new Date().getFullYear()

// 当前活动菜单
const activeMenu = computed(() => {
  return route.path
})

// 处理下拉菜单命令
const handleCommand = (command) => {
  if (command === 'logout') {
    ElMessageBox.confirm(
      '确定要退出登录吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
      .then(() => {
        // 执行登出操作
        userStore.logoutAction()
        // 跳转到登录页
        router.push('/login')
      })
      .catch(() => {
        // 取消操作
      })
  }
}
</script>

<style lang="scss" scoped>
.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .logo {
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }
  }
  
  .header-right {
    .el-dropdown-link {
      display: flex;
      align-items: center;
      cursor: pointer;
      color: white;
      
      .username {
        margin: 0 8px;
      }
    }
  }
}

.sidebar-menu {
  height: 100%;
  border-right: none;
}

.admin-main {
  padding: 20px;
}
</style> 