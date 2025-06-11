<template>
  <div class="system-container">
    <h1 class="page-title">系统监控</h1>
    
    <!-- 系统指标卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <template #header>
            <div class="card-header">
              <span>CPU使用率</span>
              <el-tag :type="getCpuTagType(metrics.cpu.percent)">
                {{ metrics.cpu.percent }}%
              </el-tag>
            </div>
          </template>
          <div class="metric-content">
            <el-progress 
              :percentage="metrics.cpu.percent" 
              :color="getCpuColor(metrics.cpu.percent)"
            ></el-progress>
            <div class="metric-info">
              <p>核心数: {{ metrics.cpu.cores }}</p>
              <p>更新时间: {{ formatTime(metrics.timestamp) }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <template #header>
            <div class="card-header">
              <span>内存使用率</span>
              <el-tag :type="getMemoryTagType(metrics.memory.percent)">
                {{ metrics.memory.percent }}%
              </el-tag>
            </div>
          </template>
          <div class="metric-content">
            <el-progress 
              :percentage="metrics.memory.percent" 
              :color="getMemoryColor(metrics.memory.percent)"
            ></el-progress>
            <div class="metric-info">
              <p>总内存: {{ formatBytes(metrics.memory.total) }}</p>
              <p>已用: {{ formatBytes(metrics.memory.used) }}</p>
              <p>可用: {{ formatBytes(metrics.memory.available) }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <template #header>
            <div class="card-header">
              <span>磁盘使用率</span>
              <el-tag :type="getDiskTagType(metrics.disk.percent)">
                {{ metrics.disk.percent }}%
              </el-tag>
            </div>
          </template>
          <div class="metric-content">
            <el-progress 
              :percentage="metrics.disk.percent" 
              :color="getDiskColor(metrics.disk.percent)"
            ></el-progress>
            <div class="metric-info">
              <p>总容量: {{ formatBytes(metrics.disk.total) }}</p>
              <p>已用: {{ formatBytes(metrics.disk.used) }}</p>
              <p>可用: {{ formatBytes(metrics.disk.free) }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card" v-if="metrics.gpu">
          <template #header>
            <div class="card-header">
              <span>GPU使用率</span>
              <el-tag :type="getGpuTagType(metrics.gpu.percent)">
                {{ metrics.gpu.percent }}%
              </el-tag>
            </div>
          </template>
          <div class="metric-content">
            <el-progress 
              :percentage="metrics.gpu.percent" 
              :color="getGpuColor(metrics.gpu.percent)"
            ></el-progress>
            <div class="metric-info">
              <p>GPU型号: {{ metrics.gpu.name || 'Apple Silicon GPU' }}</p>
              <p v-if="metrics.gpu.memory_total">总内存: {{ formatBytes(metrics.gpu.memory_total) }}</p>
              <p v-if="metrics.gpu.memory_used">已用: {{ formatBytes(metrics.gpu.memory_used) }}</p>
              <p v-if="metrics.gpu.memory_free">可用: {{ formatBytes(metrics.gpu.memory_free) }}</p>
            </div>
          </div>
        </el-card>
        <el-card shadow="hover" class="metric-card actions-card" v-else>
          <template #header>
            <div class="card-header">
              <span>系统操作</span>
            </div>
          </template>
          <div class="actions-content">
            <el-button type="primary" @click="refreshMetrics">
              刷新指标
            </el-button>
            <el-button type="primary" @click="getSystemInfo">
              系统信息
            </el-button>
            <el-button type="primary" @click="getProcessesList">
              进程列表
            </el-button>
            <el-button type="primary" @click="getSystemLogs">
              系统日志
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 系统操作按钮行 -->
    <el-row :gutter="20" v-if="metrics.gpu">
      <el-col :span="24">
        <el-card shadow="hover" class="metric-card actions-card">
          <template #header>
            <div class="card-header">
              <span>系统操作</span>
            </div>
          </template>
          <div class="actions-content-row">
            <el-button type="primary" @click="refreshMetrics">
              刷新指标
            </el-button>
            <el-button type="primary" @click="getSystemInfo">
              系统信息
            </el-button>
            <el-button type="primary" @click="getProcessesList">
              进程列表
            </el-button>
            <el-button type="primary" @click="getSystemLogs">
              系统日志
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 系统指标图表 -->
    <el-card shadow="hover" class="chart-card">
      <template #header>
        <div class="card-header">
          <span>系统资源使用趋势</span>
          <div class="header-actions">
            <el-switch
              v-model="autoRefresh"
              active-text="自动刷新"
              inactive-text="手动刷新"
            ></el-switch>
          </div>
        </div>
      </template>
      <div class="chart-container" ref="metricsChart"></div>
    </el-card>
    
    <!-- 系统信息对话框 -->
    <el-dialog
      v-model="infoDialog.visible"
      title="系统信息"
      width="70%"
    >
      <div v-loading="infoDialog.loading">
        <el-descriptions title="系统基本信息" :column="3" border>
          <el-descriptions-item label="操作系统">{{ systemInfo.system }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ systemInfo.release }}</el-descriptions-item>
          <el-descriptions-item label="主机名">{{ systemInfo.hostname }}</el-descriptions-item>
          <el-descriptions-item label="处理器">{{ systemInfo.processor }}</el-descriptions-item>
          <el-descriptions-item label="Python版本">{{ systemInfo.python_version }}</el-descriptions-item>
          <el-descriptions-item label="运行时间">{{ formatUptime(systemInfo.uptime) }}</el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions title="进程信息" :column="3" border style="margin-top: 20px">
          <el-descriptions-item label="进程ID">{{ processInfo.pid }}</el-descriptions-item>
          <el-descriptions-item label="进程名">{{ processInfo.name }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ processInfo.username }}</el-descriptions-item>
          <el-descriptions-item label="启动时间">{{ processInfo.create_time }}</el-descriptions-item>
          <el-descriptions-item label="CPU使用率">{{ processInfo.cpu_percent }}%</el-descriptions-item>
          <el-descriptions-item label="内存使用率">{{ processInfo.memory_percent }}%</el-descriptions-item>
          <el-descriptions-item label="状态">{{ processInfo.status }}</el-descriptions-item>
          <el-descriptions-item label="线程数">{{ processInfo.threads }}</el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions title="网络信息" :column="3" border style="margin-top: 20px">
          <el-descriptions-item label="发送字节">{{ formatBytes(networkInfo.bytes_sent) }}</el-descriptions-item>
          <el-descriptions-item label="接收字节">{{ formatBytes(networkInfo.bytes_recv) }}</el-descriptions-item>
          <el-descriptions-item label="连接数">{{ networkInfo.connections }}</el-descriptions-item>
          <el-descriptions-item label="发送包">{{ networkInfo.packets_sent }}</el-descriptions-item>
          <el-descriptions-item label="接收包">{{ networkInfo.packets_recv }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
    
    <!-- 进程列表对话框 -->
    <el-dialog
      v-model="processDialog.visible"
      title="进程列表"
      width="80%"
    >
      <div v-loading="processDialog.loading">
        <div class="process-header">
          <el-select v-model="processDialog.sortBy" placeholder="排序字段" style="width: 150px" @change="getProcessesList">
            <el-option label="CPU使用率" value="cpu_percent"></el-option>
            <el-option label="内存使用率" value="memory_percent"></el-option>
            <el-option label="创建时间" value="create_time"></el-option>
          </el-select>
          
          <el-input-number
            v-model="processDialog.limit"
            :min="5"
            :max="100"
            label="显示数量"
            @change="getProcessesList"
          ></el-input-number>
        </div>
        
        <el-table :data="processes" style="width: 100%">
          <el-table-column prop="pid" label="PID" width="80"></el-table-column>
          <el-table-column prop="name" label="进程名称"></el-table-column>
          <el-table-column prop="username" label="用户"></el-table-column>
          <el-table-column prop="status" label="状态" width="100"></el-table-column>
          <el-table-column prop="cpu_percent" label="CPU%" width="100">
            <template #default="scope">
              <el-progress :percentage="scope.row.cpu_percent" :format="p => p.toFixed(1) + '%'" :color="getCpuColor(scope.row.cpu_percent)"></el-progress>
            </template>
          </el-table-column>
          <el-table-column prop="memory_percent" label="内存%" width="100">
            <template #default="scope">
              <el-progress :percentage="scope.row.memory_percent" :format="p => p.toFixed(1) + '%'" :color="getMemoryColor(scope.row.memory_percent)"></el-progress>
            </template>
          </el-table-column>
          <el-table-column prop="create_time" label="创建时间" width="180"></el-table-column>
        </el-table>
      </div>
    </el-dialog>
    
    <!-- 系统日志对话框 -->
    <el-dialog
      v-model="logDialog.visible"
      title="系统日志"
      width="80%"
    >
      <div v-loading="logDialog.loading">
        <div class="log-header">
          <span>文件: {{ logDialog.file }}</span>
          <el-input-number
            v-model="logDialog.lines"
            :min="10"
            :max="1000"
            label="行数"
            @change="getSystemLogs"
          ></el-input-number>
        </div>
        
        <div class="log-content">
          <pre>{{ logDialog.content.join('') }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getSystemMetrics, getSystemInfo as apiGetSystemInfo, getProcesses, getSystemLogs as apiGetSystemLogs } from '@/api/system'
import { ElMessage } from 'element-plus'

// 图表引用
const metricsChart = ref(null)
let chartInstance = null
let refreshTimer = null

// 自动刷新
const autoRefresh = ref(true)

// 系统指标
const metrics = reactive({
  cpu: { percent: 0, cores: 0 },
  memory: { total: 0, available: 0, used: 0, percent: 0 },
  disk: { total: 0, used: 0, free: 0, percent: 0 },
  gpu: null,
  timestamp: new Date()
})

// 指标历史记录（用于图表）
const metricsHistory = reactive({
  timestamps: [],
  cpu: [],
  memory: [],
  disk: [],
  gpu: []
})

// 系统信息对话框
const infoDialog = reactive({
  visible: false,
  loading: false
})

// 系统信息
const systemInfo = reactive({
  system: '',
  release: '',
  version: '',
  machine: '',
  processor: '',
  python_version: '',
  hostname: '',
  uptime: 0
})

// 进程信息
const processInfo = reactive({
  pid: 0,
  name: '',
  username: '',
  create_time: '',
  cpu_percent: 0,
  memory_percent: 0,
  status: '',
  threads: 0
})

// 网络信息
const networkInfo = reactive({
  bytes_sent: 0,
  bytes_recv: 0,
  packets_sent: 0,
  packets_recv: 0,
  connections: 0
})

// 进程列表对话框
const processDialog = reactive({
  visible: false,
  loading: false,
  sortBy: 'cpu_percent',
  limit: 20
})

// 进程列表
const processes = ref([])

// 日志对话框
const logDialog = reactive({
  visible: false,
  loading: false,
  file: '',
  lines: 100,
  content: []
})

// 获取CPU标签类型
const getCpuTagType = (value) => {
  if (value < 50) return 'success'
  if (value < 80) return 'warning'
  return 'danger'
}

// 获取内存标签类型
const getMemoryTagType = (value) => {
  if (value < 70) return 'success'
  if (value < 90) return 'warning'
  return 'danger'
}

// 获取磁盘标签类型
const getDiskTagType = (value) => {
  if (value < 80) return 'success'
  if (value < 95) return 'warning'
  return 'danger'
}

// 获取GPU标签类型
const getGpuTagType = (value) => {
  if (value < 50) return 'success'
  if (value < 80) return 'warning'
  return 'danger'
}

// 获取CPU颜色
const getCpuColor = (value) => {
  if (value < 50) return '#67c23a'
  if (value < 80) return '#e6a23c'
  return '#f56c6c'
}

// 获取内存颜色
const getMemoryColor = (value) => {
  if (value < 70) return '#67c23a'
  if (value < 90) return '#e6a23c'
  return '#f56c6c'
}

// 获取磁盘颜色
const getDiskColor = (value) => {
  if (value < 80) return '#67c23a'
  if (value < 95) return '#e6a23c'
  return '#f56c6c'
}

// 获取GPU颜色
const getGpuColor = (value) => {
  if (value < 50) return '#67c23a'
  if (value < 80) return '#e6a23c'
  return '#f56c6c'
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '--'
  
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// 格式化字节
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 格式化运行时间
const formatUptime = (seconds) => {
  if (!seconds) return '--'
  
  const days = Math.floor(seconds / (3600 * 24))
  const hours = Math.floor((seconds % (3600 * 24)) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  let result = ''
  if (days > 0) result += `${days}天 `
  if (hours > 0 || days > 0) result += `${hours}小时 `
  result += `${minutes}分钟`
  
  return result
}

// 获取系统指标
const fetchMetrics = async () => {
  try {
    const response = await getSystemMetrics()
    
    // 更新指标
    Object.assign(metrics.cpu, response.cpu)
    Object.assign(metrics.memory, response.memory)
    Object.assign(metrics.disk, response.disk)
    metrics.timestamp = new Date(response.timestamp)
    
    // 更新GPU信息
    if (response.gpu) {
      if (!metrics.gpu) {
        metrics.gpu = {}
      }
      Object.assign(metrics.gpu, response.gpu)
    } else {
      metrics.gpu = null
    }
    
    // 更新历史记录
    const timeStr = metrics.timestamp.toLocaleTimeString()
    
    metricsHistory.timestamps.push(timeStr)
    metricsHistory.cpu.push(metrics.cpu.percent)
    metricsHistory.memory.push(metrics.memory.percent)
    metricsHistory.disk.push(metrics.disk.percent)
    
    // 更新GPU历史记录
    if (metrics.gpu) {
      metricsHistory.gpu.push(metrics.gpu.percent)
    } else if (metricsHistory.gpu.length > 0) {
      metricsHistory.gpu.push(null)
    }
    
    // 限制历史记录长度
    if (metricsHistory.timestamps.length > 10) {
      metricsHistory.timestamps.shift()
      metricsHistory.cpu.shift()
      metricsHistory.memory.shift()
      metricsHistory.disk.shift()
      if (metricsHistory.gpu.length > 0) {
        metricsHistory.gpu.shift()
      }
    }
    
    // 更新图表
    updateChart()
  } catch (error) {
    console.error('获取系统指标失败:', error)
    ElMessage.error('获取系统指标失败')
  }
}

// 刷新指标
const refreshMetrics = () => {
  fetchMetrics()
}

// 初始化图表
const initChart = () => {
  if (metricsChart.value) {
    chartInstance = echarts.init(metricsChart.value)
    
    const series = [
      {
        name: 'CPU使用率',
        type: 'line',
        data: metricsHistory.cpu,
        itemStyle: {
          color: '#f56c6c'
        }
      },
      {
        name: '内存使用率',
        type: 'line',
        data: metricsHistory.memory,
        itemStyle: {
          color: '#e6a23c'
        }
      },
      {
        name: '磁盘使用率',
        type: 'line',
        data: metricsHistory.disk,
        itemStyle: {
          color: '#409EFF'
        }
      }
    ]
    
    // 如果有GPU数据，添加到图表中
    if (metrics.gpu) {
      series.push({
        name: 'GPU使用率',
        type: 'line',
        data: metricsHistory.gpu,
        itemStyle: {
          color: '#67c23a'
        }
      })
    }
    
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
        data: metrics.gpu ? 
          ['CPU使用率', '内存使用率', '磁盘使用率', 'GPU使用率'] :
          ['CPU使用率', '内存使用率', '磁盘使用率']
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
        data: metricsHistory.timestamps
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: series
    }
    
    chartInstance.setOption(option)
  }
}

// 更新图表
const updateChart = () => {
  if (chartInstance) {
    const series = [
      {
        data: metricsHistory.cpu
      },
      {
        data: metricsHistory.memory
      },
      {
        data: metricsHistory.disk
      }
    ]
    
    // 如果有GPU数据，添加到图表中
    if (metrics.gpu && metricsHistory.gpu.length > 0) {
      series.push({
        data: metricsHistory.gpu
      })
    }
    
    chartInstance.setOption({
      xAxis: {
        data: metricsHistory.timestamps
      },
      legend: {
        data: metrics.gpu ? 
          ['CPU使用率', '内存使用率', '磁盘使用率', 'GPU使用率'] :
          ['CPU使用率', '内存使用率', '磁盘使用率']
      },
      series: series
    })
  }
}

// 获取系统信息
const getSystemInfo = async () => {
  infoDialog.visible = true
  infoDialog.loading = true
  
  try {
    const response = await apiGetSystemInfo()
    
    // 更新系统信息
    Object.assign(systemInfo, response.system)
    
    // 更新进程信息
    Object.assign(processInfo, response.process)
    
    // 更新网络信息
    Object.assign(networkInfo, response.network)
  } catch (error) {
    console.error('获取系统信息失败:', error)
    ElMessage.error('获取系统信息失败')
  } finally {
    infoDialog.loading = false
  }
}

// 获取进程列表
const getProcessesList = async () => {
  processDialog.visible = true
  processDialog.loading = true
  
  try {
    const response = await getProcesses({
      limit: processDialog.limit,
      sort_by: processDialog.sortBy
    })
    
    processes.value = response.processes
  } catch (error) {
    console.error('获取进程列表失败:', error)
    ElMessage.error('获取进程列表失败')
  } finally {
    processDialog.loading = false
  }
}

// 获取系统日志
const getSystemLogs = async () => {
  logDialog.visible = true
  logDialog.loading = true
  
  try {
    const response = await apiGetSystemLogs({
      lines: logDialog.lines
    })
    
    logDialog.file = response.file
    logDialog.content = response.content
  } catch (error) {
    console.error('获取系统日志失败:', error)
    ElMessage.error('获取系统日志失败')
  } finally {
    logDialog.loading = false
  }
}

// 监听窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// 自动刷新
const startAutoRefresh = () => {
  // 清除现有定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 设置新定时器
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchMetrics, 5000)
  }
}

onMounted(async () => {
  // 获取系统指标
  await fetchMetrics()
  
  // 初始化图表
  nextTick(() => {
    initChart()
  })
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
  
  // 启动自动刷新
  startAutoRefresh()
})

// 监听自动刷新开关变化
// 这里使用watch，但是因为使用setup script，所以需要手动实现
let oldAutoRefresh = autoRefresh.value
setInterval(() => {
  if (oldAutoRefresh !== autoRefresh.value) {
    oldAutoRefresh = autoRefresh.value
    startAutoRefresh()
  }
}, 1000)

onBeforeUnmount(() => {
  // 清除定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 销毁图表实例
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  // 移除窗口大小变化监听
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.system-container {
  .page-title {
    margin-top: 0;
    margin-bottom: 20px;
    font-size: 24px;
    font-weight: 500;
    color: #303133;
  }
  
  .metric-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .metric-content {
      padding: 10px 0;
      
      .metric-info {
        margin-top: 15px;
        font-size: 14px;
        color: #606266;
        
        p {
          margin: 5px 0;
        }
      }
    }
  }
  
  .actions-card {
    .actions-content {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    
    .actions-content-row {
      display: flex;
      flex-direction: row;
      gap: 10px;
    }
  }
  
  .chart-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .chart-container {
      height: 400px;
    }
  }
  
  .process-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 15px;
  }
  
  .log-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 15px;
    align-items: center;
  }
  
  .log-content {
    max-height: 500px;
    overflow-y: auto;
    background-color: #f5f7fa;
    border-radius: 4px;
    
    pre {
      padding: 10px;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
      font-family: monospace;
    }
  }
}
</style> 