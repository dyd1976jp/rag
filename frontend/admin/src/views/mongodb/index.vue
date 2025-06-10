<template>
  <div class="mongodb-container">
    <h1 class="page-title">MongoDB管理</h1>
    
    <el-row :gutter="20">
      <!-- 集合列表 -->
      <el-col :span="6">
        <el-card shadow="hover" class="collections-card">
          <template #header>
            <div class="card-header">
              <span>集合列表</span>
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
      
      <!-- 文档管理 -->
      <el-col :span="18">
        <el-card shadow="hover" class="documents-card">
          <template #header>
            <div class="card-header">
              <span>{{ currentCollection || '请选择集合' }}</span>
              <div v-if="currentCollection" class="header-actions">
                <el-input
                  v-model="filterQuery"
                  placeholder="过滤条件 (JSON格式)"
                  style="width: 250px; margin-right: 10px;"
                  @keyup.enter="refreshDocuments"
                >
                  <template #append>
                    <el-button @click="refreshDocuments">过滤</el-button>
                  </template>
                </el-input>
                
                <el-button 
                  type="primary"
                  @click="openAddDocumentDialog"
                >添加文档</el-button>
              </div>
            </div>
          </template>
          
          <div v-if="!currentCollection" class="select-hint">
            <el-empty description="请从左侧选择集合"></el-empty>
          </div>
          
          <div v-else class="documents-content" v-loading="documentsLoading">
            <!-- 分页控制 -->
            <div class="pagination-controls">
              <el-pagination
                v-model:current-page="pagination.currentPage"
                v-model:page-size="pagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                :total="pagination.total"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              />
            </div>
            
            <!-- 文档表格 -->
            <el-table
              :data="documents"
              style="width: 100%"
              max-height="500"
              :default-sort="{ prop: '_id', order: 'descending' }"
            >
              <el-table-column prop="_id" label="ID" width="250" sortable />
              
              <el-table-column label="内容">
                <template #default="scope">
                  <div class="document-preview">
                    <!-- 预览文档内容，最多显示100字符 -->
                    {{ formatDocumentPreview(scope.row) }}
                    
                    <!-- 查看详情按钮 -->
                    <el-button
                      type="text"
                      @click="viewDocument(scope.row)"
                    >查看详情</el-button>
                  </div>
                </template>
              </el-table-column>
              
              <el-table-column label="操作" width="150">
                <template #default="scope">
                  <el-button
                    size="small"
                    @click="editDocument(scope.row)"
                  >编辑</el-button>
                  
                  <el-button
                    size="small"
                    type="danger"
                    @click="deleteDocument(scope.row)"
                  >删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 添加/编辑文档对话框 -->
    <el-dialog
      v-model="documentDialog.visible"
      :title="documentDialog.isEdit ? '编辑文档' : '添加文档'"
      width="70%"
    >
      <div class="document-editor">
        <el-input
          v-model="documentDialog.content"
          type="textarea"
          :rows="15"
          placeholder="请输入JSON格式的文档内容"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="documentDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="saveDocument">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 查看文档对话框 -->
    <el-dialog
      v-model="viewDialog.visible"
      title="文档详情"
      width="70%"
    >
      <div class="document-viewer">
        <pre>{{ viewDialog.content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCollections, getCollectionData, insertDocument, updateDocuments, deleteDocuments } from '@/api/mongodb'

const route = useRoute()
const router = useRouter()

// 集合列表
const collections = ref([])
const collectionsLoading = ref(false)

// 当前选中的集合
const currentCollection = ref('')

// 文档列表
const documents = ref([])
const documentsLoading = ref(false)

// 过滤查询
const filterQuery = ref('')

// 分页配置
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 文档对话框
const documentDialog = reactive({
  visible: false,
  isEdit: false,
  content: '',
  currentId: null
})

// 查看文档对话框
const viewDialog = reactive({
  visible: false,
  content: ''
})

// 获取集合列表
const fetchCollections = async () => {
  collectionsLoading.value = true
  
  try {
    const response = await getCollections()
    collections.value = response.collections
    
    // 如果URL中有集合参数，选中该集合
    const collectionParam = route.query.collection
    if (collectionParam && collections.value.includes(collectionParam)) {
      currentCollection.value = collectionParam
      fetchDocuments()
    }
  } catch (error) {
    console.error('获取集合列表失败:', error)
    ElMessage.error('获取集合列表失败')
  } finally {
    collectionsLoading.value = false
  }
}

// 获取文档列表
const fetchDocuments = async () => {
  if (!currentCollection.value) return
  
  documentsLoading.value = true
  
  try {
    // 构建请求参数
    const params = {
      skip: (pagination.currentPage - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }
    
    // 添加过滤条件
    if (filterQuery.value) {
      try {
        // 验证JSON格式
        JSON.parse(filterQuery.value)
        params.filter = filterQuery.value
      } catch (e) {
        ElMessage.warning('过滤条件格式不正确，请输入有效的JSON')
      }
    }
    
    const response = await getCollectionData(currentCollection.value, params)
    documents.value = response.documents
    pagination.total = response.total_documents
  } catch (error) {
    console.error('获取文档列表失败:', error)
    ElMessage.error('获取文档列表失败')
  } finally {
    documentsLoading.value = false
  }
}

// 选择集合
const selectCollection = (index) => {
  currentCollection.value = index
  // 重置分页
  pagination.currentPage = 1
  // 获取文档列表
  fetchDocuments()
  
  // 更新URL参数
  router.push({
    query: { ...route.query, collection: index }
  })
}

// 处理分页大小变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchDocuments()
}

// 处理页码变化
const handleCurrentChange = (page) => {
  pagination.currentPage = page
  fetchDocuments()
}

// 刷新集合列表
const refreshCollections = () => {
  fetchCollections()
}

// 刷新文档列表
const refreshDocuments = () => {
  pagination.currentPage = 1
  fetchDocuments()
}

// 格式化文档预览
const formatDocumentPreview = (document) => {
  try {
    // 移除_id字段，避免显示过长
    const preview = { ...document }
    delete preview._id
    
    // 转换为JSON字符串并限制长度
    const json = JSON.stringify(preview)
    return json.length > 100 ? json.substring(0, 100) + '...' : json
  } catch (e) {
    return '无法预览'
  }
}

// 查看文档
const viewDocument = (document) => {
  viewDialog.content = JSON.stringify(document, null, 2)
  viewDialog.visible = true
}

// 打开添加文档对话框
const openAddDocumentDialog = () => {
  documentDialog.isEdit = false
  documentDialog.content = '{\n  \n}'
  documentDialog.currentId = null
  documentDialog.visible = true
}

// 编辑文档
const editDocument = (document) => {
  documentDialog.isEdit = true
  documentDialog.content = JSON.stringify(document, null, 2)
  documentDialog.currentId = document._id
  documentDialog.visible = true
}

// 保存文档
const saveDocument = async () => {
  // 验证JSON格式
  try {
    const documentData = JSON.parse(documentDialog.content)
    
    if (documentDialog.isEdit) {
      // 编辑模式
      const id = documentDialog.currentId
      // 创建更新查询
      const query = { _id: id }
      const update = { $set: documentData }
      
      // 执行更新
      try {
        await updateDocuments(currentCollection.value, query, update)
        ElMessage.success('文档更新成功')
        documentDialog.visible = false
        fetchDocuments()
      } catch (error) {
        console.error('更新文档失败:', error)
        ElMessage.error('更新文档失败')
      }
    } else {
      // 添加模式
      try {
        await insertDocument(currentCollection.value, documentData)
        ElMessage.success('文档添加成功')
        documentDialog.visible = false
        fetchDocuments()
      } catch (error) {
        console.error('添加文档失败:', error)
        ElMessage.error('添加文档失败')
      }
    }
  } catch (e) {
    ElMessage.error('文档格式不正确，请输入有效的JSON')
  }
}

// 删除文档
const deleteDocument = (document) => {
  ElMessageBox.confirm(
    '确定要删除此文档吗？此操作不可恢复。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      try {
        await deleteDocuments(currentCollection.value, { _id: document._id })
        ElMessage.success('文档删除成功')
        fetchDocuments()
      } catch (error) {
        console.error('删除文档失败:', error)
        ElMessage.error('删除文档失败')
      }
    })
    .catch(() => {
      // 取消操作
    })
}

onMounted(() => {
  // 获取集合列表
  fetchCollections()
})
</script>

<style lang="scss" scoped>
.mongodb-container {
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
  
  .documents-card {
    height: calc(100vh - 160px);
    display: flex;
    flex-direction: column;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .header-actions {
        display: flex;
        align-items: center;
      }
    }
    
    .select-hint {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .documents-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      
      .pagination-controls {
        margin-bottom: 10px;
        display: flex;
        justify-content: flex-end;
      }
      
      .document-preview {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 500px;
      }
    }
  }
  
  .document-viewer {
    max-height: 500px;
    overflow-y: auto;
    
    pre {
      white-space: pre-wrap;
      word-break: break-all;
      background-color: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
    }
  }
}
</style> 