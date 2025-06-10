<template>
  <div class="vectorstore-container">
    <h1 class="page-title">向量存储管理</h1>
    
    <el-row :gutter="20">
      <!-- 集合列表 -->
      <el-col :span="6">
        <el-card shadow="hover" class="collections-card">
          <template #header>
            <div class="card-header">
              <span>向量集合</span>
              <el-button type="primary" size="small" @click="refreshCollections">刷新</el-button>
            </div>
          </template>
          
          <div class="collections-list" v-loading="collectionsLoading">
            <el-menu
              :default-active="currentCollection"
              @select="selectCollection"
              class="collection-menu"
            >
              <el-menu-item 
                v-for="collection in collections" 
                :key="collection"
                :index="collection"
              >{{ collection }}</el-menu-item>
            </el-menu>
            
            <div v-if="collections.length === 0" class="empty-list">
              <el-empty description="暂无集合"></el-empty>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 集合详情 -->
      <el-col :span="18">
        <div v-if="!currentCollection" class="select-hint">
          <el-empty description="请从左侧选择集合"></el-empty>
        </div>
        
        <template v-else>
          <!-- 统计信息 -->
          <el-card shadow="hover" class="stats-card" v-loading="statsLoading">
            <template #header>
              <div class="card-header">
                <span>{{ currentCollection }} 统计信息</span>
                <div class="header-actions">
                  <el-button type="primary" size="small" @click="flushCollection">刷新数据</el-button>
                  <el-button type="danger" size="small" @click="confirmPurgeCollection">清空集合</el-button>
                </div>
              </div>
            </template>
            
            <el-descriptions :column="3" border>
              <el-descriptions-item label="集合名称">{{ stats.collection_name }}</el-descriptions-item>
              <el-descriptions-item label="向量数量">{{ stats.row_count }}</el-descriptions-item>
              <el-descriptions-item label="索引类型">{{ stats.index_info ? stats.index_info.index_type : '未知' }}</el-descriptions-item>
            </el-descriptions>
            
            <div class="schema-info" v-if="stats.schema">
              <h3>集合结构</h3>
              <el-table :data="schemaItems" style="width: 100%">
                <el-table-column prop="field" label="字段名" />
                <el-table-column prop="type" label="类型" />
                <el-table-column prop="dimension" label="维度" />
              </el-table>
            </div>
          </el-card>
          
          <!-- 向量样本 -->
          <el-card shadow="hover" class="samples-card" v-loading="samplesLoading">
            <template #header>
              <div class="card-header">
                <span>向量样本</span>
                <el-button type="primary" size="small" @click="refreshSamples">刷新样本</el-button>
              </div>
            </template>
            
            <div v-if="samples.length === 0" class="empty-samples">
              <el-empty description="暂无数据"></el-empty>
            </div>
            
            <div v-else class="samples-list">
              <el-collapse>
                <el-collapse-item 
                  v-for="(sample, index) in samples" 
                  :key="index"
                  :title="`样本 ${index + 1} - ID: ${sample.id || '无ID'}`"
                >
                  <div class="sample-content">
                    <pre>{{ formatSample(sample) }}</pre>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-card>
        </template>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getVectorCollections, 
  getCollectionStats, 
  getCollectionSample,
  flushCollection as apiFlushCollection,
  purgeCollection as apiPurgeCollection
} from '@/api/vectorstore'

const route = useRoute()
const router = useRouter()

// 集合列表
const collections = ref([])
const collectionsLoading = ref(false)

// 当前选中的集合
const currentCollection = ref('')

// 统计信息
const stats = reactive({
  collection_name: '',
  row_count: 0,
  index_info: null,
  schema: null
})
const statsLoading = ref(false)

// 样本数据
const samples = ref([])
const samplesLoading = ref(false)

// 计算出模式字段列表
const schemaItems = computed(() => {
  if (!stats.schema) return []
  
  return Object.entries(stats.schema).map(([field, type]) => {
    // 分析字段类型
    const dimension = type.includes('VECTOR') 
      ? type.match(/\((\d+)\)/) 
        ? type.match(/\((\d+)\)/)[1] 
        : '未知'
      : '-'
    
    return {
      field,
      type: type.split('(')[0],
      dimension
    }
  })
})

// 获取集合列表
const fetchCollections = async () => {
  collectionsLoading.value = true
  
  try {
    const response = await getVectorCollections()
    collections.value = response.collections
    
    // 如果URL中有集合参数，选中该集合
    const collectionParam = route.query.collection
    if (collectionParam && collections.value.includes(collectionParam)) {
      currentCollection.value = collectionParam
      fetchCollectionData()
    }
  } catch (error) {
    console.error('获取向量集合列表失败:', error)
    ElMessage.error('获取向量集合列表失败')
  } finally {
    collectionsLoading.value = false
  }
}

// 获取集合统计信息和样本
const fetchCollectionData = async () => {
  if (!currentCollection.value) return
  
  // 获取统计信息
  fetchCollectionStats()
  
  // 获取样本数据
  fetchSamples()
}

// 获取集合统计信息
const fetchCollectionStats = async () => {
  if (!currentCollection.value) return
  
  statsLoading.value = true
  
  try {
    const response = await getCollectionStats(currentCollection.value)
    
    // 更新统计信息
    Object.assign(stats, response)
  } catch (error) {
    console.error('获取统计信息失败:', error)
    ElMessage.error('获取统计信息失败')
  } finally {
    statsLoading.value = false
  }
}

// 获取样本数据
const fetchSamples = async () => {
  if (!currentCollection.value) return
  
  samplesLoading.value = true
  
  try {
    const response = await getCollectionSample(currentCollection.value, 5)
    samples.value = response.samples
  } catch (error) {
    console.error('获取样本数据失败:', error)
    ElMessage.error('获取样本数据失败')
  } finally {
    samplesLoading.value = false
  }
}

// 选择集合
const selectCollection = (index) => {
  currentCollection.value = index
  
  // 获取集合数据
  fetchCollectionData()
  
  // 更新URL参数
  router.push({
    query: { ...route.query, collection: index }
  })
}

// 刷新集合列表
const refreshCollections = () => {
  fetchCollections()
}

// 刷新样本
const refreshSamples = () => {
  fetchSamples()
}

// 格式化样本显示
const formatSample = (sample) => {
  try {
    // 移除向量数据（太长了）
    const formatted = { ...sample }
    if (formatted.vector) {
      formatted.vector = `[向量数据 - ${
        Array.isArray(formatted.vector) ? formatted.vector.length : '未知'
      } 维]`
    }
    
    return JSON.stringify(formatted, null, 2)
  } catch (e) {
    return JSON.stringify(sample)
  }
}

// 刷新集合
const flushCollection = async () => {
  if (!currentCollection.value) return
  
  try {
    await apiFlushCollection(currentCollection.value)
    ElMessage.success('集合刷新成功')
    
    // 重新获取统计信息
    fetchCollectionStats()
  } catch (error) {
    console.error('刷新集合失败:', error)
    ElMessage.error('刷新集合失败')
  }
}

// 确认清空集合
const confirmPurgeCollection = () => {
  ElMessageBox.confirm(
    `确定要清空集合 ${currentCollection.value} 中的所有数据吗？此操作不可恢复！`,
    '危险操作',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'danger'
    }
  )
    .then(() => {
      purgeCollection()
    })
    .catch(() => {
      // 取消操作
    })
}

// 清空集合
const purgeCollection = async () => {
  if (!currentCollection.value) return
  
  try {
    const response = await apiPurgeCollection(currentCollection.value)
    
    ElMessage.success(`清空成功，已删除 ${response.deleted_count} 条记录`)
    
    // 重新获取集合数据
    fetchCollectionData()
  } catch (error) {
    console.error('清空集合失败:', error)
    ElMessage.error('清空集合失败')
  }
}

onMounted(() => {
  // 获取集合列表
  fetchCollections()
})
</script>

<style lang="scss" scoped>
.vectorstore-container {
  .page-title {
    margin-top: 0;
    margin-bottom: 20px;
    font-size: 24px;
    font-weight: 500;
    color: #303133;
  }
  
  .collections-card {
    height: calc(100vh - 160px);
    display: flex;
    flex-direction: column;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .collections-list {
      flex: 1;
      overflow-y: auto;
      
      .collection-menu {
        border-right: none;
      }
      
      .empty-list {
        padding: 20px 0;
      }
    }
  }
  
  .select-hint {
    height: calc(100vh - 160px);
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: white;
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  }
  
  .stats-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .header-actions {
        display: flex;
        gap: 10px;
      }
    }
    
    .schema-info {
      margin-top: 20px;
      
      h3 {
        margin-top: 0;
        margin-bottom: 10px;
        font-size: 16px;
        font-weight: 500;
        color: #303133;
      }
    }
  }
  
  .samples-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .empty-samples {
      padding: 20px 0;
    }
    
    .samples-list {
      .sample-content {
        pre {
          white-space: pre-wrap;
          word-break: break-all;
          background-color: #f5f7fa;
          padding: 10px;
          border-radius: 4px;
          margin: 0;
        }
      }
    }
  }
}
</style> 