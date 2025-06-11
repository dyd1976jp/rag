<template>
  <div class="dashboard-container">
    <h1 class="page-title">系统概览</h1>
    
    <!-- 数据概览卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <template #header>
            <div class="card-header">
              <span>MongoDB文档总数</span>
            </div>
          </template>
          <div class="card-content">
            <div class="data-value">{{ stats.mongoDocuments || '-' }}</div>
            <div class="data-label">总文档数</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <template #header>
            <div class="card-header">
              <span>向量数据总数</span>
            </div>
          </template>
          <div class="card-content">
            <div class="data-value">{{ stats.vectorEntities || '-' }}</div>
            <div class="data-label">总向量数</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <template #header>
            <div class="card-header">
              <span>CPU使用率</span>
            </div>
          </template>
          <div class="card-content">
            <div class="data-value">{{ stats.cpuPercent ? `${stats.cpuPercent}%` : '-' }}</div>
            <div class="data-label">当前使用率</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <template #header>
            <div class="card-header">
              <span>内存使用率</span>
            </div>
          </template>
          <div class="card-content">
            <div class="data-value">{{ stats.memoryPercent ? `${stats.memoryPercent}%` : '-' }}</div>
            <div class="data-label">当前使用率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 图表 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>系统资源使用</span>
            </div>
          </template>
          <div class="chart-container" ref="systemChart"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>数据分布</span>
            </div>
          </template>
          <div class="chart-container" ref="dataChart"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 数据列表 -->
    <el-card shadow="hover" class="list-card">
      <template #header>
        <div class="card-header">
          <span>数据集合概览</span>
          <el-button type="primary" size="small" @click="refreshData">刷新</el-button>
        </div>
      </template>
      
      <el-table :data="collections" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="集合名称" />
        <el-table-column prop="count" label="文档数量" />
        <el-table-column prop="type" label="类型" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button 
              size="small"
              @click="navigateToCollection(scope.row)"
            >管理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getSystemMetrics } from '@/api/system'
import { getCollections } from '@/api/mongodb'
import { getVectorCollections } from '@/api/vectorstore'
import { ElMessage } from 'element-plus'

const router = useRouter()
const systemChart = ref(null)
const dataChart = ref(null)
let systemChartInstance = null
let dataChartInstance = null
let refreshTimer = null

// 加载状态
const loading = ref(false)

// 统计数据
const stats = reactive({
  mongoDocuments: 0,
  vectorEntities: 0,
  cpuPercent: 0,
  memoryPercent: 0
})

// 集合列表
const collections = ref([])

// 获取数据
const fetchData = async () => {
  loading.value = true
  
  try {
    // 获取系统指标
    const metrics = await getSystemMetrics()
    stats.cpuPercent = metrics.cpu.percent
    stats.memoryPercent = metrics.memory.percent
    
    // 更新系统资源图表
    updateSystemChart(metrics)
    
    // 获取MongoDB集合
    const mongoCollections = await getCollections()
    
    // 获取向量存储集合
    const vectorCollections = await getVectorCollections()
    
    // 处理集合数据
    processCollections(mongoCollections.collections, vectorCollections.collections)
    
    // 更新数据分布图表
    updateDataChart()
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

// 处理集合数据
const processCollections = (mongoCollections, vectorCollections) => {
  const result = []
  let totalDocuments = 0
  
  // 处理MongoDB集合
  mongoCollections.forEach(name => {
    // 这里假设文档数为0，实际应用中应该获取每个集合的文档数
    const count = 0
    totalDocuments += count
    
    result.push({
      name,
      count,
      type: 'MongoDB'
    })
  })
  
  // 处理向量存储集合
  vectorCollections.forEach(name => {
    // 这里假设向量数为0，实际应用中应该获取每个集合的向量数
    const count = 0
    
    result.push({
      name,
      count,
      type: '向量存储'
    })
  })
  
  // 更新集合列表和统计数据
  collections.value = result
  stats.mongoDocuments = totalDocuments
  // 向量实体数需要单独获取
}

// 初始化图表
const initCharts = () => {
  // 初始化系统资源图表
  if (systemChart.value) {
    systemChartInstance = echarts.init(systemChart.value)
    
    // 设置初始选项
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        }
      },
      legend: {
        data: ['CPU使用率', '内存使用率', '磁盘使用率']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: []
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: [
        {
          name: 'CPU使用率',
          type: 'line',
          data: []
        },
        {
          name: '内存使用率',
          type: 'line',
          data: []
        },
        {
          name: '磁盘使用率',
          type: 'line',
          data: []
        }
      ]
    }
    
    systemChartInstance.setOption(option)
  }
  
  // 初始化数据分布图表
  if (dataChart.value) {
    dataChartInstance = echarts.init(dataChart.value)
    
    // 设置初始选项
    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 10,
        data: ['MongoDB集合', '向量存储']
      },
      series: [
        {
          name: '数据分布',
          type: 'pie',
          radius: ['50%', '70%'],
          avoidLabelOverlap: false,
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '20',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: [
            { value: 0, name: 'MongoDB集合' },
            { value: 0, name: '向量存储' }
          ]
        }
      ]
    }
    
    dataChartInstance.setOption(option)
  }
}

// 更新系统资源图表
const updateSystemChart = (metrics) => {
  if (!systemChartInstance) return
  
  // 获取当前时间
  const now = new Date()
  const timeStr = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds()
  
  // 获取当前图表配置
  const option = systemChartInstance.getOption()
  
  // 更新X轴数据
  option.xAxis[0].data.push(timeStr)
  if (option.xAxis[0].data.length > 10) {
    option.xAxis[0].data.shift()
  }
  
  // 更新系列数据
  option.series[0].data.push(metrics.cpu.percent)
  option.series[1].data.push(metrics.memory.percent)
  option.series[2].data.push(metrics.disk.percent)
  
  if (option.series[0].data.length > 10) {
    option.series[0].data.shift()
    option.series[1].data.shift()
    option.series[2].data.shift()
  }
  
  // 应用更新
  systemChartInstance.setOption(option)
}

// 更新数据分布图表
const updateDataChart = () => {
  if (!dataChartInstance) return
  
  // 更新饼图数据
  dataChartInstance.setOption({
    series: [
      {
        data: [
          { value: stats.mongoDocuments, name: 'MongoDB集合' },
          { value: stats.vectorEntities, name: '向量存储' }
        ]
      }
    ]
  })
}

// 刷新数据
const refreshData = () => {
  fetchData()
}

// 导航到集合管理页面
const navigateToCollection = (row) => {
  if (row.type === 'MongoDB') {
    router.push({
      path: '/mongodb',
      query: { collection: row.name }
    })
  } else {
    router.push({
      path: '/vectorstore',
      query: { collection: row.name }
    })
  }
}

// 监听窗口大小变化
const handleResize = () => {
  if (systemChartInstance) {
    systemChartInstance.resize()
  }
  
  if (dataChartInstance) {
    dataChartInstance.resize()
  }
}

onMounted(() => {
  // 初始化图表
  initCharts()
  
  // 获取数据
  fetchData()
  
  // 设置定时刷新
  refreshTimer = setInterval(fetchData, 60000)
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  // 清除定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 销毁图表实例
  if (systemChartInstance) {
    systemChartInstance.dispose()
  }
  
  if (dataChartInstance) {
    dataChartInstance.dispose()
  }
  
  // 移除窗口大小变化监听
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.dashboard-container {
  .page-title {
    margin-top: 0;
    margin-bottom: 20px;
    font-size: 24px;
    font-weight: 500;
    color: #303133;
  }
  
  .data-card {
    margin-bottom: 20px;
    
    .card-content {
      text-align: center;
      
      .data-value {
        font-size: 30px;
        font-weight: bold;
        color: #409EFF;
      }
      
      .data-label {
        margin-top: 10px;
        font-size: 14px;
        color: #606266;
      }
    }
  }
  
  .chart-row {
    margin-bottom: 20px;
  }
  
  .chart-card {
    .chart-container {
      height: 300px;
    }
  }
  
  .list-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
  
  .card-header {
    font-weight: bold;
  }
}
</style> 