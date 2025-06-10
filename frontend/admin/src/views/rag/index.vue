<!-- RAG管理页面 -->
<template>
  <div class="rag-management">
    <h1>RAG管理</h1>
    
    <!-- 服务状态提示 -->
    <el-alert
      v-if="!ragServiceAvailable"
      title="RAG服务不可用"
      type="error"
      description="Milvus向量数据库或嵌入模型服务未启动。请确保相关服务已经启动并正常运行。"
      :closable="false"
      show-icon
    >
      <template #default>
        <div class="service-instructions">
          <p><strong>启动步骤：</strong></p>
          <ol>
            <li>确保Docker已安装并运行</li>
            <li>启动Milvus向量数据库：<code>docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone</code></li>
            <li>启动后端服务（如需重启）</li>
            <li>刷新页面检查服务状态</li>
          </ol>
          <el-button type="primary" @click="checkServiceStatus">检查服务状态</el-button>
        </div>
      </template>
    </el-alert>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>文档管理</span>
            </div>
          </template>
          
          <!-- 文本输入区域 -->
          <div class="text-input-section">
            <el-input
              v-model="textContent"
              type="textarea"
              :rows="10"
              placeholder="请输入或粘贴文本内容"
              resize="vertical"
            />
            <div class="text-input-actions">
              <el-button type="primary" @click="handleTextSubmit" :disabled="!textContent.trim()">处理文本</el-button>
            </div>
          </div>

          <!-- 分割线 -->
          <el-divider>或者</el-divider>

          <!-- 文档上传和预览区域 -->
          <div class="document-upload-section">
            <el-upload
              class="upload-demo"
              drag
              action="/api/v1/rag/documents/upload"
              :headers="uploadHeaders"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              :on-change="handleFileChange"
              :auto-upload="false"
              ref="uploadRef"
              multiple
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 PDF、TXT 和 Markdown 文件
                </div>
              </template>
            </el-upload>

            <!-- 文本预览区域 -->
            <div v-if="selectedFile" class="text-preview-container">
              <div class="text-preview-header">
                <span>文档内容预览</span>
                <span class="text-preview-info">{{ selectedFile.name }} - {{ previewContent ? previewContent.length : 0 }} 字符</span>
              </div>
              <div v-if="selectedFile.name.endsWith('.pdf')" class="text-preview-loading">
                <el-empty description="PDF文件不支持直接预览" :image-size="60">
                  <template #description>
                    <p>PDF文件需要上传后才能查看切割结果</p>
                  </template>
                </el-empty>
              </div>
              <div v-else-if="previewContent" class="text-preview-content">
                {{ previewContent }}
              </div>
              <div v-else class="text-preview-loading">
                <el-empty description="正在加载文件内容..." :image-size="60">
                  <template #description>
                    <p>正在加载文件内容...</p>
                    <p class="loading-tip">支持预览 TXT 和 Markdown 文件</p>
                  </template>
                </el-empty>
              </div>
            </div>

            <!-- 上传操作按钮 -->
            <div class="upload-actions" v-if="selectedFile">
              <el-button type="primary" @click="showSplitPreview" :disabled="!ragServiceAvailable">预览文档切割</el-button>
              <el-button type="success" @click="submitUpload" :disabled="!ragServiceAvailable">开始上传</el-button>
            </div>

            <!-- 上传进度 -->
            <div v-if="isUploading" class="upload-progress">
              <span>文档处理进度:</span>
              <el-progress :percentage="uploadProgress" :format="format => `${format}%`" />
            </div>
          </div>

          <!-- 文档列表 -->
          <el-table
            v-loading="loading"
            :data="documents"
            style="width: 100%; margin-top: 20px;"
            border
          >
            <el-table-column prop="id" label="ID" width="280" />
            <el-table-column prop="file_name" label="文件名" />
            <el-table-column prop="segments_count" label="段落数" width="100" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)">
                  {{ getStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="scope">
                <el-button 
                  size="small" 
                  type="primary" 
                  @click="searchDocument(scope.row)"
                  :disabled="!ragServiceAvailable"
                >搜索</el-button>
                <el-button 
                  size="small" 
                  type="primary" 
                  plain
                  @click="previewDocument(scope.row)"
                  :disabled="!ragServiceAvailable"
                >预览</el-button>
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="deleteDocument(scope.row)"
                  :disabled="!ragServiceAvailable"
                >删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 无数据或服务不可用时的提示 -->
          <div v-if="documents.length === 0 && !loading" class="empty-data">
            <p v-if="ragServiceAvailable">暂无文档，请上传新文档</p>
            <p v-else>RAG服务不可用，请先启动所需服务</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 搜索对话框 -->
    <el-dialog
      v-model="searchDialogVisible"
      title="文档搜索"
      width="70%"
    >
      <el-form>
        <el-form-item label="搜索查询">
          <el-input 
            v-model="searchQuery" 
            placeholder="输入搜索内容" 
            @keyup.enter="performSearch"
          ></el-input>
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="searchAllUsers">搜索所有用户的文档</el-checkbox>
          <el-tooltip content="启用此选项将搜索系统中所有用户上传的文档，而不仅仅是您自己的文档" placement="top">
            <el-icon class="el-icon--right"><info-filled /></el-icon>
          </el-tooltip>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="includeParent">包含父文档</el-checkbox>
          <el-tooltip content="启用此选项将返回匹配片段的父文档，提供更完整的上下文" placement="top">
            <el-icon class="el-icon--right"><info-filled /></el-icon>
          </el-tooltip>
        </el-form-item>
      </el-form>
      
      <div v-if="searchResults.length > 0" class="search-results">
        <h3>搜索结果</h3>
        <div 
          v-for="(result, index) in searchResults" 
          :key="index"
          class="result-item"
        >
          <div class="result-content">{{ result.content }}</div>
          <div v-if="result.parent" class="parent-content">
            <div class="parent-header">父文档内容:</div>
            <div class="parent-text">{{ result.parent.content }}</div>
          </div>
          <div class="result-meta">
            <span>文件名: {{ result.metadata.file_name }}</span>
            <span>相关度分数: {{ (result.metadata.score * 100).toFixed(2) }}%</span>
          </div>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="searchDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="performSearch">搜索</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文档"
      width="80%"
      destroy-on-close
    >
      <el-tabs v-model="activeUploadTab">
        <el-tab-pane label="上传文件" name="upload">
          <el-upload
            class="upload-demo"
            drag
            action="/api/v1/rag/documents/upload"
            :headers="uploadHeaders"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :on-change="handleFileChange"
            :auto-upload="false"
            ref="uploadRef"
            multiple
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF、TXT 和 Markdown 文件
              </div>
            </template>
          </el-upload>
          
          <!-- 调试信息 -->
          <div class="debug-info" style="margin: 10px 0; padding: 10px; background: #f0f0f0; font-size: 12px;">
            <div>selectedFile: {{ selectedFile?.name || '无' }}</div>
            <div>文件类型: {{ selectedFile?.type || '无' }}</div>
            <div>previewContent长度: {{ previewContent?.length || 0 }}</div>
          </div>

          <!-- 修改文本预览区域 -->
          <div v-if="selectedFile" class="text-preview-container">
            <div class="text-preview-header">
              <span>文档内容预览</span>
              <span class="text-preview-info">{{ selectedFile.name }} - {{ previewContent ? previewContent.length : 0 }} 字符</span>
            </div>
            <div v-if="selectedFile.name.endsWith('.pdf')" class="text-preview-loading">
              <el-empty description="PDF文件不支持直接预览" :image-size="60">
                <template #description>
                  <p>PDF文件需要上传后才能查看切割结果</p>
                </template>
              </el-empty>
            </div>
            <div v-else-if="previewContent" class="text-preview-content">
              {{ previewContent }}
            </div>
            <div v-else class="text-preview-loading">
              <el-empty description="正在加载文件内容..." :image-size="60">
                <template #description>
                  <p>正在加载文件内容...</p>
                  <p class="loading-tip">支持预览 TXT 和 Markdown 文件</p>
                </template>
              </el-empty>
            </div>
          </div>
          
          <div class="upload-actions">
            <el-button type="primary" @click="showSplitPreview">预览文档切割</el-button>
            <el-button type="success" @click="submitUpload">开始上传</el-button>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="切割参数设置" name="settings">
          <el-form :model="splitSettings" label-width="180px">
            <el-form-item label="分块大小 (字符数)">
              <el-slider 
                v-model="splitSettings.chunkSize" 
                :min="100" 
                :max="2000" 
                :step="50"
                show-input
              />
              <div class="setting-description">
                每个文档块的最大字符数。较小的块更适合精确查询，较大的块包含更多上下文。
              </div>
            </el-form-item>
            
            <el-form-item label="块重叠大小 (字符数)">
              <el-slider 
                v-model="splitSettings.chunkOverlap" 
                :min="0" 
                :max="200" 
                :step="10"
                show-input
              />
              <div class="setting-description">
                连续块之间重叠的字符数。增加重叠可以提高连贯性，但会增加存储需求。
              </div>
            </el-form-item>
            
            <el-form-item label="按段落分割">
              <el-switch v-model="splitSettings.splitByParagraph" />
              <div class="setting-description">
                启用后，文档将首先按段落分割，然后再应用分块。这有助于保持段落的完整性。
              </div>
            </el-form-item>
            
            <el-form-item label="按句子分割">
              <el-switch v-model="splitSettings.splitBySentence" />
              <div class="setting-description">
                启用后，长段落将在句子边界处分割，以保持句子的完整性。
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="切割预览" name="preview">
          <div v-if="previewLoading" class="preview-loading">
            <el-skeleton :rows="10" animated />
          </div>
          
          <div v-else-if="!previewContent && previewSegments.length === 0" class="preview-empty">
            <el-empty description="请先选择文件并点击'预览文档切割'按钮">
              <el-button type="primary" @click="activeUploadTab = 'upload'">选择文件</el-button>
            </el-empty>
          </div>
          
          <div v-else>
            <div class="preview-stats">
              <div class="stat-item">
                <div class="stat-label">总字符数</div>
                <div class="stat-value">{{ previewContent ? previewContent.length : '未知' }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">总段落数</div>
                <div class="stat-value">{{ previewSegments.length }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">平均段落长度</div>
                <div class="stat-value">{{ getAverageSegmentLength() }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">切割参数</div>
                <div class="stat-value-small">
                  <div>块大小: {{ splitSettings.chunkSize }}</div>
                  <div>重叠: {{ splitSettings.chunkOverlap }}</div>
                </div>
              </div>
            </div>
            
            <div class="preview-content">
              <div 
                class="preview-original-text"
                ref="previewTextRef"
              >
                <div v-if="previewSegments.length === 0" class="no-segments-message">
                  <el-empty description="根据当前设置，文档无法被切割成段落">
                    <el-button type="primary" size="small" @click="activeUploadTab = 'settings'">调整切割参数</el-button>
                  </el-empty>
                </div>
                <div 
                  v-else
                  v-for="segment in previewSegments" 
                  :key="segment.id"
                  class="segment-highlight"
                  :style="getSegmentStyle(segment)"
                  @mouseover="highlightSegment(segment.id)"
                  @mouseout="unhighlightSegment()"
                >
                  {{ segment.content }}
                </div>
              </div>
              
              <div class="preview-segments">
                <h4>段落列表 ({{ previewSegments.length }})</h4>
                <div v-if="previewSegments.length === 0" class="empty-segments-tip">
                  没有生成段落，请调整切割参数
                </div>
                <div 
                  v-else
                  v-for="segment in previewSegments" 
                  :key="segment.id"
                  class="segment-item"
                  :class="{ 'segment-active': activeSegmentIndex === segment.id }"
                  @mouseover="highlightSegment(segment.id)"
                  @mouseout="unhighlightSegment()"
                >
                  <div class="segment-header">
                    <span class="segment-number">段落 #{{ segment.id + 1 }}</span>
                    <span class="segment-length">{{ segment.length }} 字符</span>
                  </div>
                  <div class="segment-content">{{ segment.content }}</div>
                </div>
              </div>
            </div>
            
            <div class="preview-actions">
              <el-button @click="activeUploadTab = 'settings'">调整参数</el-button>
              <el-button type="primary" @click="refreshPreview">刷新预览</el-button>
              <el-button type="success" @click="submitUpload">确认并上传</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
      
      <div v-if="isUploading" class="upload-progress">
        <span>文档处理进度:</span>
        <el-progress :percentage="uploadProgress" :format="format => `${format}%`" />
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false" :disabled="isUploading">关闭</el-button>
          <el-button type="primary" @click="submitUpload" :disabled="isUploading">上传</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 文档预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="文档内容预览"
      width="70%"
      destroy-on-close
    >
      <div v-loading="previewLoading" class="preview-container">
        <div v-if="documentSegments.length > 0" class="segments-container">
          <div class="segments-header">
            <div class="segments-stats">
              <span>总段落数：{{ documentSegments.length }}</span>
              <span>|</span>
              <span>总字符数：{{ getTotalCharCount() }}</span>
            </div>
          </div>
          <div class="segments-content">
            <div 
              v-for="segment in documentSegments" 
              :key="segment.id"
              class="segment-item"
            >
              <div class="segment-header">
                <span class="segment-number">段落 #{{ segment.id + 1 }}</span>
                <span class="segment-length">{{ segment.content.length }} 字符</span>
              </div>
              <div class="segment-content">{{ segment.content }}</div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无内容" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, InfoFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { getRAGStatus, getDocuments, deleteDocument as apiDeleteDocument, searchDocuments, previewDocumentSplit, getDocumentStatus } from '@/api/rag'

// 用户存储
const userStore = useUserStore()

// 状态变量
const loading = ref(false)
const documents = ref([])
const searchDialogVisible = ref(false)
const uploadDialogVisible = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const currentDocId = ref('')
const ragServiceAvailable = ref(true) // 默认假设服务可用
const searchAllUsers = ref(false)
const includeParent = ref(false)

// 上传相关
const uploadRef = ref(null)
const activeUploadTab = ref('upload')
const selectedFile = ref(null)
const previewContent = ref('')
const previewSegments = ref([])
const previewLoading = ref(false)
const activeSegmentIndex = ref(null)
const previewTextRef = ref(null)

// 切割设置
const splitSettings = reactive({
  chunkSize: 512,
  chunkOverlap: 50,
  splitByParagraph: true,
  splitBySentence: true
})

// 上传头信息
const uploadHeaders = {
  Authorization: `Bearer ${userStore.token}`
}

// 在data部分添加以下变量
const uploadingDocId = ref('')
const uploadProgress = ref(0)
const progressTimer = ref(null)
const isUploading = ref(false)

// 添加预览相关的状态变量
const previewDialogVisible = ref(false)
const documentSegments = ref([])

// 添加文本输入相关的状态变量
const textContent = ref('')

// 检查RAG服务状态
const checkServiceStatus = async () => {
  try {
    const response = await getRAGStatus()
    ragServiceAvailable.value = response.available
    
    if (response.available) {
      ElMessage.success('RAG服务已可用')
      fetchDocuments() // 重新获取文档列表
    } else {
      ElMessage.error(`RAG服务不可用: ${response.message}`)
    }
  } catch (error) {
    console.error('检查服务状态失败:', error)
    ragServiceAvailable.value = false
    ElMessage.error('检查服务状态失败，服务可能不可用')
  }
}

// 获取所有文档
const fetchDocuments = async () => {
  loading.value = true
  try {
    const response = await getDocuments()
    documents.value = response.documents || []
    
    // 检查服务是否可用
    ragServiceAvailable.value = response.success !== false
    
    // 如果返回错误且提示RAG服务不可用
    if (response.success === false && response.message && response.message.includes('RAG服务不可用')) {
      ragServiceAvailable.value = false
      console.warn('RAG服务不可用:', response.message)
    }
  } catch (error) {
    console.error('获取文档失败:', error)
    ElMessage.error('获取文档列表失败')
    // 假设服务可能不可用
    ragServiceAvailable.value = false
  } finally {
    loading.value = false
  }
}

// 状态相关函数
const getStatusType = (status) => {
  switch(status) {
    case 'ready': return 'success'
    case 'completed': return 'success'
    case 'processing': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (status) => {
  switch(status) {
    case 'ready': return '已完成'
    case 'completed': return '已完成'
    case 'processing': return '处理中'
    case 'failed': return '失败'
    default: return status
  }
}

// 删除文档
const deleteDocument = (document) => {
  if (!ragServiceAvailable.value) {
    ElMessage.warning('RAG服务不可用，无法删除文档')
    return
  }
  
  ElMessageBox.confirm(
    `确认删除文档 "${document.file_name}"?`,
    '警告',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const response = await apiDeleteDocument(document.id)
      
      if (response.success) {
        ElMessage.success(`文档 "${document.file_name}" 删除成功`)
        fetchDocuments() // 刷新列表
      } else {
        // 根据错误代码显示不同的错误提示
        let errorMessage = response.message || '删除失败'
        let errorType = 'error'
        
        switch (response.error_code) {
          case 'PERMISSION_DENIED':
            errorMessage = '您没有权限删除此文档'
            break
          case 'DOCUMENT_NOT_FOUND':
            errorMessage = '文档不存在或已被删除'
            break
          case 'RAG_SERVICE_UNAVAILABLE':
            errorMessage = 'RAG服务不可用，请确保Milvus和嵌入模型服务已启动'
            ragServiceAvailable.value = false
            break
          case 'VECTOR_DELETE_FAILED':
            // 向量删除失败但文档已删除，显示为警告而非错误
            errorMessage = '文档已删除，但清理向量数据时出现问题：' + response.warning
            errorType = 'warning'
            fetchDocuments() // 仍然刷新列表
            break
          case 'DB_DELETE_FAILED':
            errorMessage = '数据库删除操作失败，请稍后重试'
            break
          default:
            if (response.message && response.message.includes('RAG服务不可用')) {
              ragServiceAvailable.value = false
              errorMessage = 'RAG服务不可用，请确保相关服务已启动'
            }
        }
        
        // 显示错误信息
        ElMessage({
          message: errorMessage,
          type: errorType,
          duration: 5000 // 显示时间更长，让用户有足够时间阅读
        })
        
        // 记录到控制台以便调试
        console.error('删除文档失败:', response)
      }
    } catch (error) {
      console.error('删除文档失败:', error)
      
      // 检查是否为网络错误或服务器错误
      if (error.response) {
        // 服务器返回了错误状态码
        const status = error.response.status
        if (status === 403) {
          ElMessage.error('权限不足，无法删除此文档')
        } else if (status === 404) {
          ElMessage.error('文档不存在或已被删除')
          fetchDocuments() // 刷新列表
        } else if (status === 503) {
          ElMessage.error('RAG服务暂时不可用，请稍后重试')
          ragServiceAvailable.value = false
        } else {
          ElMessage.error(`删除失败: ${error.response.data?.message || '未知错误'}`)
        }
      } else if (error.request) {
        // 请求已发出，但没有收到响应
        ElMessage.error('服务器无响应，请检查网络连接')
      } else {
        // 请求设置时出错
        ElMessage.error('删除文档失败: ' + error.message)
      }
    }
  }).catch(() => {
    // 用户取消操作
  })
}

// 搜索文档
const searchDocument = (document) => {
  if (!ragServiceAvailable.value) {
    ElMessage.warning('RAG服务不可用，无法执行搜索')
    return
  }
  
  currentDocId.value = document.id
  searchDialogVisible.value = true
  searchQuery.value = ''
  searchResults.value = []
}

const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  if (!ragServiceAvailable.value) {
    ElMessage.warning('RAG服务不可用，无法执行搜索')
    searchDialogVisible.value = false
    return
  }
  
  try {
    const response = await searchDocuments({
      query: searchQuery.value,
      search_all: searchAllUsers.value,
      include_parent: includeParent.value
    })
    
    if (response.success) {
      searchResults.value = response.results || []
      
      if (searchResults.value.length === 0) {
        ElMessage.info('未找到相关内容')
      }
    } else {
      // 检查服务可用性
      if (response.message && response.message.includes('RAG服务不可用')) {
        ragServiceAvailable.value = false
        searchDialogVisible.value = false
      }
      
      ElMessage.error(`搜索失败: ${response.message}`)
    }
  } catch (error) {
    console.error('搜索文档失败:', error)
    ElMessage.error('搜索文档失败')
  }
}

// 上传相关方法
const showUploadDialog = () => {
  if (!ragServiceAvailable.value) {
    ElMessage.warning('RAG服务不可用，无法上传文档')
    return
  }
  
  uploadDialogVisible.value = true
  activeUploadTab.value = 'upload'
  previewContent.value = ''
  previewSegments.value = []
}

// 修改文件处理逻辑
const handleFileChange = async (file, fileList) => {
  console.log('===== 文件选择变更开始 =====');
  console.log('文件选择变更:', file);
  console.log('文件列表:', fileList);
  
  // 清空之前的预览内容
  previewContent.value = '';
  
  // 保存选中的文件
  selectedFile.value = file.raw;
  console.log('已设置selectedFile:', selectedFile.value?.name);
  
  // 如果是文本文件，读取内容以便预览
  const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  console.log('文件扩展名:', extension);
  
  if (extension === '.txt' || extension === '.md') {
    console.log('文本文件，开始读取内容');
    try {
      const content = await readFileContent(file.raw);
      console.log(`文件内容已读取，长度: ${content.length}字符`);
      previewContent.value = content;
    } catch (error) {
      console.error('读取文件内容失败:', error);
      ElMessage.error('读取文件内容失败');
      previewContent.value = '';
    }
  } else if (extension === '.pdf') {
    // PDF文件无法直接预览文本内容
    previewContent.value = '';
    console.log('选择了PDF文件，无法直接预览内容');
    ElMessage.info('PDF文件需要上传后才能查看切割结果');
  }
  console.log('===== 文件选择变更结束 =====');
};

// 添加文件读取辅助函数
const readFileContent = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        resolve(e.target.result);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = (e) => reject(new Error('文件读取错误'));
    reader.readAsText(file);
  });
};

// 修改beforeUpload方法
const beforeUpload = async (file) => {
  console.log('===== beforeUpload方法开始 =====');
  console.log('检查文件:', file.name);
  
  if (!ragServiceAvailable.value) {
    console.log('RAG服务不可用，拒绝上传');
    ElMessage.warning('RAG服务不可用，无法上传文档');
    return false;
  }
  
  const validTypes = ['.pdf', '.txt', '.md'];
  const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  
  console.log('文件扩展名:', extension);
  if (!validTypes.includes(extension)) {
    console.log('不支持的文件类型:', extension);
    ElMessage.error(`不支持的文件类型: ${extension}`);
    return false;
  }
  
  // 保存文件引用到selectedFile变量
  console.log('设置selectedFile:', file.name);
  selectedFile.value = file;
  
  // 如果是文本文件，读取内容以便预览
  if (extension === '.txt' || extension === '.md') {
    console.log('读取文本文件内容');
    try {
      const content = await readFileContent(file);
      console.log(`文件内容已读取，长度: ${content.length}字符`);
      previewContent.value = content;
    } catch (error) {
      console.error('读取文件内容失败:', error);
      ElMessage.error('读取文件内容失败');
      previewContent.value = '';
    }
  } else if (extension === '.pdf') {
    // PDF文件无法直接预览文本内容
    previewContent.value = '';
    console.log('选择了PDF文件，无法直接预览内容');
    ElMessage.info('PDF文件需要上传后才能查看切割结果');
  }
  
  console.log('===== beforeUpload方法结束 =====');
  return true;
}

const submitUpload = () => {
  console.log('===== 调用submitUpload方法开始 =====');
  if (uploadRef.value) {
    // 判断当前是否为预览模式
    const isPreviewMode = activeUploadTab.value === 'preview';
    console.log('当前模式:', isPreviewMode ? '预览模式' : '上传模式');
    console.log('当前活动标签页:', activeUploadTab.value);
    
    // 如果是PDF文件，先上传文件，然后在成功回调中获取切割结果并预览
    if (selectedFile.value && selectedFile.value.name.toLowerCase().endsWith('.pdf')) {
      console.log('处理PDF文件上传:', selectedFile.value.name);
      
      // 设置上传参数
      const uploadParams = {
        chunk_size: splitSettings.chunkSize,
        chunk_overlap: splitSettings.chunkOverlap,
        split_by_paragraph: splitSettings.splitByParagraph,
        split_by_sentence: splitSettings.splitBySentence,
        preview_only: true  // 在预览时总是设置为true
      };
      console.log('上传参数:', uploadParams);
      uploadRef.value.data = uploadParams;
      
      if (isPreviewMode) {
        previewLoading.value = true;
        console.log('PDF预览模式：开始上传获取预览结果');
        ElMessage.info('正在上传PDF文件并获取预览结果...');
      } else {
        console.log('PDF上传模式：开始正常上传');
        ElMessage.info('正在上传PDF文件...');
      }
      
      console.log('提交上传请求...');
      uploadRef.value.submit();
      return;
    }
    
    // 对于文本文件，如果还没有内容，先尝试预览
    if (!previewContent.value) {
      console.log('文本文件但没有内容，先调用预览');
      ElMessage.warning('请先预览文档切割结果');
      showSplitPreview();
      return;
    }
    
    // 设置上传参数
    const uploadParams = {
      chunk_size: splitSettings.chunkSize,
      chunk_overlap: splitSettings.chunkOverlap,
      split_by_paragraph: splitSettings.splitByParagraph,
      split_by_sentence: splitSettings.splitBySentence,
      preview_only: isPreviewMode  // 根据当前标签页决定是否为预览模式
    };
    console.log('文本文件上传参数:', uploadParams);
    uploadRef.value.data = uploadParams;
    
    // 如果是预览模式，直接提交
    if (isPreviewMode) {
      console.log('文本文件预览模式：直接提交获取预览');
      ElMessage.info('正在获取预览结果...');
      uploadRef.value.submit();
      return;
    }
    
    // 正常上传模式，需要确认
    console.log('文本文件上传模式：显示确认对话框');
    ElMessageBox.confirm(
      '确认上传并处理文档？',
      '确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'info'
      }
    ).then(() => {
      console.log('用户确认上传，提交请求');
      uploadRef.value.submit();
    }).catch(() => {
      console.log('用户取消上传');
      // 用户取消上传
    });
  } else {
    console.log('uploadRef不存在，无法上传');
  }
  console.log('===== 调用submitUpload方法结束 =====');
}

const handleUploadSuccess = (response) => {
  console.log('===== 上传成功回调开始 =====');
  console.log('上传成功响应:', response);
  console.log('当前activeUploadTab:', activeUploadTab.value);
  
  if (response.success) {
    // 检查是否为预览模式
    if (response.preview_mode) {
      console.log('收到预览模式响应，处理预览结果');
      // 这是预览结果，显示预览内容
      ElMessage.success('文档预览获取成功');
      previewLoading.value = false;
      
      // 设置预览内容
      if (response.segments && response.segments.length > 0) {
        console.log(`收到 ${response.segments.length} 个预览段落`);
        // 确保每个段落都有唯一ID
        previewSegments.value = response.segments.map((segment, index) => ({
          ...segment,
          id: index
        }));
        
        // 切换到预览标签页
        console.log('切换到预览标签页');
        activeUploadTab.value = 'preview';
        
        // 等待DOM更新后滚动到顶部
        nextTick(() => {
          if (previewTextRef.value) {
            previewTextRef.value.scrollTop = 0;
            console.log('已滚动预览内容到顶部');
          }
        });
      } else {
        console.log('未收到有效的预览段落');
        ElMessage.warning('未获取到有效的预览内容');
      }
      
      return;
    }
    
    // 正常上传流程
    console.log('正常上传成功，开始监控处理进度');
    ElMessage.success('文档上传成功');
    // 保存文档ID并开始监控进度
    uploadingDocId.value = response.doc_id;
    uploadProgress.value = 0;
    isUploading.value = true;
    
    // 开始轮询文档处理状态
    startProgressMonitor();
  } else {
    console.log('上传响应显示失败:', response.message);
    previewLoading.value = false;
    
    // 检查服务可用性
    if (response.message && response.message.includes('RAG服务不可用')) {
      console.log('检测到RAG服务不可用');
      ragServiceAvailable.value = false;
      uploadDialogVisible.value = false;
    }
    
    ElMessage.error(`上传失败: ${response.message}`);
  }
  console.log('===== 上传成功回调结束 =====');
}

const handleUploadError = (error) => {
  console.log('===== 上传错误回调开始 =====');
  console.error('上传文档失败:', error);
  console.log('错误详情:', {
    status: error.status,
    statusText: error.statusText,
    response: error.response,
  });
  previewLoading.value = false;
  
  // 尝试解析错误信息
  let errorMessage = '上传文档失败';
  if (error.response) {
    try {
      console.log('尝试解析错误响应');
      const responseData = JSON.parse(error.response);
      console.log('解析后的错误响应:', responseData);
      errorMessage = responseData.message || errorMessage;
    } catch (e) {
      console.error('解析错误响应失败:', e);
    }
  }
  
  console.log('显示错误消息:', errorMessage);
  ElMessage.error(errorMessage);
  
  // 可能是服务不可用导致的错误
  if (error.status === 503 || error.status === 500) {
    console.log('检测到服务器错误，标记RAG服务不可用');
    ragServiceAvailable.value = false;
    uploadDialogVisible.value = false;
  }
  console.log('===== 上传错误回调结束 =====');
}

// 开始监控文档处理进度
const startProgressMonitor = () => {
  // 清除可能存在的旧定时器
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
  }
  
  // 创建新的轮询定时器
  progressTimer.value = setInterval(async () => {
    if (!uploadingDocId.value) {
      clearInterval(progressTimer.value)
      return
    }
    
    try {
      const response = await getDocumentStatus(uploadingDocId.value)
      if (response.success && response.document) {
        const doc = response.document
        
        // 更新进度
        if (doc.processing_details && doc.processing_details.progress !== undefined) {
          uploadProgress.value = doc.processing_details.progress
        }
        
        // 如果文档状态为ready、completed或failed，停止轮询
        if (doc.status === 'ready' || doc.status === 'completed' || doc.status === 'failed') {
          clearInterval(progressTimer.value)
          isUploading.value = false
          
          if (doc.status === 'ready' || doc.status === 'completed') {
            ElMessage.success('文档处理完成')
            uploadDialogVisible.value = false
            fetchDocuments() // 刷新文档列表
          } else {
            ElMessage.error(`文档处理失败: ${doc.error || '未知错误'}`)
          }
        }
      }
    } catch (error) {
      console.error('获取文档状态失败:', error)
    }
  }, 2000) // 每2秒轮询一次
}

// 预览文档切割
const showSplitPreview = async () => {
  console.log('===== 调用showSplitPreview方法开始 =====');
  console.log('uploadRef:', uploadRef.value);
  if (uploadRef.value) {
    console.log('uploadRef.uploadFiles:', uploadRef.value.uploadFiles);
  }
  console.log('selectedFile:', selectedFile.value);
  
  // 检查是否有选择文件
  if (!selectedFile.value) {
    console.log('未找到selectedFile，尝试从上传组件获取');
    // 检查是否有通过el-upload组件选择的文件
    if (uploadRef.value && uploadRef.value.uploadFiles && uploadRef.value.uploadFiles.length > 0) {
      // 使用第一个选择的文件
      selectedFile.value = uploadRef.value.uploadFiles[0].raw;
      console.log('从上传组件中获取文件:', selectedFile.value.name);
    } else {
      // 尝试从el-upload组件的内部获取文件
      const uploadInput = document.querySelector('.el-upload__input');
      console.log('uploadInput:', uploadInput);
      if (uploadInput && uploadInput.files && uploadInput.files.length > 0) {
        selectedFile.value = uploadInput.files[0];
        console.log('从DOM中获取文件:', selectedFile.value.name);
      } else {
        console.log('未找到任何文件，显示警告');
        ElMessage.warning('请先选择文件');
        return;
      }
    }
  }
  
  // 获取文件扩展名
  const extension = selectedFile.value.name.substring(selectedFile.value.name.lastIndexOf('.')).toLowerCase();
  console.log('文件扩展名:', extension);
  
  // 如果是PDF文件，通过上传接口获取预览
  if (extension === '.pdf') {
    console.log('PDF文件，切换到预览标签页并设置加载状态');
    activeUploadTab.value = 'preview';
    previewLoading.value = true;
    previewSegments.value = [];
    
    ElMessage.info('PDF文件需要上传后才能预览切割结果，正在处理中...');
    console.log('调用submitUpload方法处理PDF预览');
    
    // 通过submitUpload方法上传PDF并获取预览
    submitUpload();
    return;
  }
  
  // 对于文本文件，如果还没有内容，尝试再次读取
  if (!previewContent.value && (extension === '.txt' || extension === '.md')) {
    console.log('文本文件，但previewContent为空，开始读取文件内容');
    previewLoading.value = true;
    const reader = new FileReader();
    reader.onload = async (e) => {
      previewContent.value = e.target.result;
      console.log('文件内容已读取，长度:', previewContent.value.length);
      activeUploadTab.value = 'preview';
      console.log('调用refreshPreview获取预览结果');
      await refreshPreview();
      previewLoading.value = false;
    };
    reader.onerror = (e) => {
      console.error('读取文件失败:', e);
      ElMessage.error('读取文件失败，请重新选择文件');
      previewLoading.value = false;
    };
    reader.readAsText(selectedFile.value);
    return;
  }
  
  // 如果已有内容可以预览
  if (previewContent.value) {
    console.log('已有文件内容，直接刷新预览');
    activeUploadTab.value = 'preview';
    await refreshPreview();
  } else {
    // 对于PDF文件，显示特殊提示
    if (extension === '.pdf') {
      console.log('PDF文件但未执行上传流程，显示提示');
      ElMessage.info('PDF文件需要上传后才能预览切割结果，请点击"开始上传"按钮');
    } else {
      console.log('没有可预览的内容，显示警告');
      ElMessage.warning('没有可预览的内容，请选择文本文件');
    }
  }
  console.log('===== 调用showSplitPreview方法结束 =====');
}

// 刷新预览
const refreshPreview = async () => {
  console.log('===== 刷新预览开始 =====');
  previewLoading.value = true;
  previewSegments.value = []; // 清空之前的结果
  
  try {
    // 确保有内容可以预览
    if (!previewContent.value || previewContent.value.trim().length === 0) {
      console.log('没有可预览的内容，显示警告');
      ElMessage.warning('没有可预览的内容');
      previewLoading.value = false;
      return;
    }
    
    const previewParams = {
      chunk_size: splitSettings.chunkSize,
      chunk_overlap: splitSettings.chunkOverlap,
      split_by_paragraph: splitSettings.splitByParagraph,
      split_by_sentence: splitSettings.splitBySentence,
      content_length: previewContent.value.length
    };
    
    console.log('发送预览请求，参数:', previewParams);
    
    const response = await previewDocumentSplit({
      content: previewContent.value,
      chunk_size: splitSettings.chunkSize,
      chunk_overlap: splitSettings.chunkOverlap,
      split_by_paragraph: splitSettings.splitByParagraph,
      split_by_sentence: splitSettings.splitBySentence
    });
    
    console.log('预览响应:', response);
    
    if (response.success) {
      // 确保每个段落都有唯一ID
      previewSegments.value = (response.segments || []).map((segment, index) => ({
        ...segment,
        id: index // 确保id是索引，而不是从后端返回的可能重复的id
      }));
      
      console.log(`成功获取 ${previewSegments.value.length} 个预览段落`);
      
      // 如果没有段落，显示提示
      if (previewSegments.value.length === 0) {
        console.log('未生成预览段落，显示警告');
        ElMessage.warning('根据当前设置，文档无法被切割成段落');
      } else {
        ElMessage.success(`成功生成 ${previewSegments.value.length} 个段落`);
      }
      
      // 切换到预览标签页
      console.log('切换到预览标签页');
      activeUploadTab.value = 'preview';
      
      // 等待DOM更新后滚动到顶部
      nextTick(() => {
        if (previewTextRef.value) {
          previewTextRef.value.scrollTop = 0;
          console.log('已滚动预览内容到顶部');
        }
      });
    } else {
      console.log('预览请求失败:', response.message);
      ElMessage.error(`预览失败: ${response.message || '未知错误'}`);
    }
  } catch (error) {
    console.error('预览文档切割失败:', error);
    
    // 提供更详细的错误信息
    let errorMessage = '预览文档切割失败';
    if (error.response) {
      // 服务器返回了错误响应
      const { status, data } = error.response;
      console.log('服务器错误响应:', { status, data });
      errorMessage += `，服务器返回: ${status}`;
      if (data && data.detail) {
        errorMessage += ` - ${data.detail}`;
      }
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      console.log('服务器无响应');
      errorMessage += '，服务器无响应，请检查后端服务是否运行';
    } else {
      // 请求配置有误
      errorMessage += `，${error.message}`;
    }
    
    console.log('显示错误消息:', errorMessage);
    ElMessage.error(errorMessage);
  } finally {
    previewLoading.value = false;
    console.log('===== 刷新预览结束 =====');
  }
}

// 高亮段落
const highlightSegment = (index) => {
  activeSegmentIndex.value = index
}

// 取消高亮
const unhighlightSegment = () => {
  activeSegmentIndex.value = null
}

// 获取段落样式
const getSegmentStyle = (segment) => {
  return {
    backgroundColor: activeSegmentIndex.value === segment.id ? 'rgba(64, 158, 255, 0.1)' : 'transparent',
    border: activeSegmentIndex.value === segment.id ? '1px dashed #409EFF' : '1px solid #f0f0f0',
    borderRadius: '4px',
    padding: '4px 8px',
    margin: '4px 0',
    transition: 'all 0.3s'
  }
}

// 计算平均段落长度
const getAverageSegmentLength = () => {
  if (previewSegments.value.length === 0) return 0
  
  const totalLength = previewSegments.value.reduce((sum, segment) => sum + segment.length, 0)
  return Math.round(totalLength / previewSegments.value.length)
}

// 预览文档
const previewDocument = async (document) => {
  if (!ragServiceAvailable.value) {
    ElMessage.warning('RAG服务不可用，无法预览文档')
    return
  }

  previewDialogVisible.value = true
  previewLoading.value = true
  documentSegments.value = []

  try {
    // 获取文档详情
    const response = await getDocumentStatus(document.id)
    if (response.success && response.document && response.document.segments) {
      documentSegments.value = response.document.segments.map((segment, index) => ({
        ...segment,
        id: index
      }))
    } else {
      ElMessage.warning('获取文档内容失败')
    }
  } catch (error) {
    console.error('预览文档失败:', error)
    ElMessage.error('预览文档失败')
  } finally {
    previewLoading.value = false
  }
}

// 计算总字符数
const getTotalCharCount = () => {
  return documentSegments.value.reduce((total, segment) => total + segment.content.length, 0)
}

// 处理文本提交
const handleTextSubmit = async () => {
  if (!textContent.value.trim()) {
    ElMessage.warning('请输入文本内容')
    return
  }

  // 将文本内容设置为预览内容
  previewContent.value = textContent.value
  
  // 显示预览
  await showSplitPreview()
}

// 生命周期钩子
onMounted(() => {
  fetchDocuments()
})

// 在组件卸载时清除定时器
onBeforeUnmount(() => {
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
  }
})
</script>

<style scoped>
.rag-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-results {
  margin-top: 20px;
}

.result-item {
  border-left: 3px solid #409eff;
  padding: 10px;
  margin-bottom: 15px;
  background-color: #f9f9f9;
}

.result-content {
  margin-bottom: 10px;
  line-height: 1.5;
}

.result-meta {
  font-size: 12px;
  color: #666;
  display: flex;
  justify-content: space-between;
}

.mt-20 {
  margin-top: 20px;
}

.service-instructions {
  margin-top: 10px;
}

.service-instructions code {
  background-color: #f5f5f5;
  padding: 2px 5px;
  border-radius: 3px;
  font-family: monospace;
}

.empty-data {
  text-align: center;
  padding: 30px 0;
  color: #909399;
}

.parent-content {
  margin: 10px 0;
  padding: 10px;
  background-color: #f0f8ff;
  border-left: 3px solid #1e90ff;
  border-radius: 3px;
}

.parent-header {
  font-weight: bold;
  margin-bottom: 5px;
  color: #1e90ff;
}

.parent-text {
  font-size: 0.9em;
  color: #444;
  max-height: 200px;
  overflow-y: auto;
}

/* 上传相关样式 */
.upload-actions {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.setting-description {
  font-size: 12px;
  color: #606266;
  margin-top: 5px;
  line-height: 1.4;
}

/* 预览相关样式 */
.preview-loading {
  padding: 20px;
}

.preview-empty {
  padding: 40px 0;
  text-align: center;
}

.preview-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.preview-content {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.preview-original-text {
  flex: 1;
  padding: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
  line-height: 1.5;
  white-space: pre-wrap;
  background-color: #fafafa;
}

.preview-segments {
  flex: 1;
  padding: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
}

.segment-item {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  transition: all 0.3s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.segment-item:hover {
  border-color: #c6e2ff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.segment-active {
  background-color: rgba(64, 158, 255, 0.1);
  border-color: #409EFF !important;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2) !important;
}

.segment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.segment-number {
  font-weight: bold;
  color: #409EFF;
}

.segment-length {
  color: #909399;
  font-size: 12px;
}

.segment-content {
  font-size: 14px;
  color: #606266;
  white-space: pre-wrap;
  max-height: 100px;
  overflow-y: auto;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.upload-progress {
  margin-bottom: 15px;
  width: 100%;
}

.stat-value-small {
  font-size: 14px;
  color: #606266;
  line-height: 1.4;
}

.no-segments-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  width: 100%;
}

.empty-segments-tip {
  text-align: center;
  padding: 40px 0;
  color: #909399;
  font-style: italic;
}

.preview-original-text {
  flex: 1;
  padding: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
  line-height: 1.5;
  white-space: pre-wrap;
  background-color: #fafafa;
}

.segment-highlight {
  position: relative;
  margin-bottom: 8px;
  line-height: 1.6;
}

.segment-highlight:hover {
  background-color: rgba(64, 158, 255, 0.05);
}

/* 添加文本预览相关样式 */
.text-preview-container {
  margin-top: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #fff;
  min-height: 200px;
}

.text-preview-header {
  padding: 12px 15px;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f5f7fa;
}

.text-preview-info {
  font-size: 13px;
  color: #909399;
}

.text-preview-content {
  padding: 15px;
  height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #606266;
  background-color: #fafafa;
}

.text-preview-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  background-color: #fafafa;
}

.loading-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

/* 文档预览样式 */
.preview-container {
  min-height: 300px;
}

.segments-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.segments-header {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.segments-stats {
  display: flex;
  gap: 12px;
  color: #606266;
  font-size: 14px;
}

.segments-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
}

.segment-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
}

.segment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.segment-number {
  font-weight: bold;
  color: #409eff;
}

.segment-length {
  color: #909399;
  font-size: 12px;
}

.segment-content {
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
}

/* 文档上传区域样式 */
.document-upload-section {
  margin-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 20px;
}

.upload-demo {
  width: 100%;
}

.text-preview-container {
  margin-top: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #fff;
}

.text-preview-header {
  padding: 12px 15px;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f5f7fa;
}

.text-preview-info {
  font-size: 13px;
  color: #909399;
}

.text-preview-content {
  padding: 15px;
  height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #606266;
  background-color: #fafafa;
}

.text-preview-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  background-color: #fafafa;
}

.loading-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.upload-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 15px;
}

.upload-progress {
  margin-top: 15px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

/* 添加文本输入区域样式 */
.text-input-section {
  margin-bottom: 20px;
}

.text-input-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

/* 分割线样式 */
.el-divider {
  margin: 24px 0;
}
</style> 