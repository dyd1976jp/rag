import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/layout/index.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'el-icon-s-home' }
      },
      {
        path: 'rag',
        name: 'RAG',
        component: () => import('@/views/rag/index.vue'),
        meta: { title: 'RAG管理', icon: 'el-icon-s-data' }
      },
      {
        path: 'mongodb',
        name: 'MongoDB',
        component: () => import('@/views/mongodb/index.vue'),
        meta: { title: 'MongoDB管理', icon: 'el-icon-s-grid' }
      },
      {
        path: 'vectorstore',
        name: 'VectorStore',
        component: () => import('@/views/vectorstore/index.vue'),
        meta: { title: '向量存储管理', icon: 'el-icon-s-operation' }
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/system/index.vue'),
        meta: { title: '系统监控', icon: 'el-icon-s-platform' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404'
  },
  {
    path: '/404',
    name: '404',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404', requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - RAG系统管理后台` : 'RAG系统管理后台'
  
  // 认证逻辑
  const userStore = useUserStore()
  
  // 判断页面是否需要认证
  if (to.meta.requiresAuth !== false) {
    // 需要认证，检查用户是否已登录
    if (!userStore.token) {
      // 未登录，重定向到登录页
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }
  
  // 已登录或页面不需要认证
  next()
})

export default router 