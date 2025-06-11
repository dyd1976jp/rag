import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import DocumentPreview from '../components/DocumentPreview';
import { Document, PreviewSegment } from '../utils/types';
import { 
  DocumentCollection, 
  DocumentCollectionCreate 
} from '../types/documentCollection';
import * as documentCollectionApi from '../api/documentCollections';

const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [previewSegments, setPreviewSegments] = useState<PreviewSegment[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [previewDocumentId, setPreviewDocumentId] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [chunkSize, setChunkSize] = useState(512);
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [splitByParagraph, setSplitByParagraph] = useState(true);
  const [splitBySentence, setSplitBySentence] = useState(true);
  const [textContent, setTextContent] = useState('');

  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [isAddingToCollection, setIsAddingToCollection] = useState(false);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [showCollectionDialog, setShowCollectionDialog] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newCollectionDesc, setNewCollectionDesc] = useState('');
  const [newCollectionTags, setNewCollectionTags] = useState<string[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);

  const [previewDialogVisible, setPreviewDialogVisible] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [documentSegments, setDocumentSegments] = useState<any[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('');
  const [selectedDocumentName, setSelectedDocumentName] = useState<string>('');

  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/auth');
      return;
    }
    fetchDocuments();
    fetchCollections();
  }, [navigate]);

  const fetchDocuments = async () => {
    try {
      setErrorMessage('');
      const response = await axios.get('/api/v1/rag/documents', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.data && response.data.documents) {
        setDocuments(response.data.documents.map((doc: any) => ({
          ...doc,
          created_at: new Date(doc.created_at)
        })));
      }
    } catch (error) {
      console.error('获取文档列表失败:', error);
      setErrorMessage('获取文档列表失败，请检查网络连接');
    }
  };

  const fetchCollections = async () => {
    try {
      console.log('Fetching collections...');
      const response = await documentCollectionApi.getCollections();
      console.log('Collections response:', response);
      
      if (!response.data) {
        throw new Error('No data in response');
      }
      
      if (!response.data.data || !response.data.data.collections) {
        console.error('Unexpected response structure:', response.data);
        throw new Error('Invalid response structure');
      }
      
      console.log('Setting collections:', response.data.data.collections);
      setCollections(response.data.data.collections);
    } catch (error) {
      console.error('获取文档集列表失败:', error);
      setErrorMessage(error instanceof Error ? error.message : '获取文档集列表失败');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    setSelectedFile(file);
    setErrorMessage('');
  };

  const handlePreview = async (e?: React.MouseEvent, documentId?: string) => {
    if (!selectedFile && !documentId) {
      setErrorMessage('请先选择文件');
      return;
    }

    setIsUploading(true);
    setErrorMessage('');
    
    try {
      const formData = new FormData();
      if (selectedFile) {
        formData.append('file', selectedFile);
      }
      formData.append('chunk_size', chunkSize.toString());
      formData.append('chunk_overlap', chunkOverlap.toString());
      formData.append('split_by_paragraph', splitByParagraph.toString());
      formData.append('split_by_sentence', splitBySentence.toString());
      
      const response = await axios.post('/api/v1/rag/documents/preview-split', formData, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data && response.data.success) {
        setPreviewSegments(response.data.segments);
        setPreviewDocumentId(documentId || '');
        setShowPreview(true);
        setSuccessMessage('预览成功');
      } else {
        setErrorMessage(response.data.message || '预览失败');
      }
    } catch (error: any) {
      console.error('预览失败:', error);
      setErrorMessage(error.response?.data?.message || '预览失败');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setErrorMessage('请先选择文件');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setErrorMessage('');
    
    const formData = new FormData();
    if (selectedFile) {
      formData.append('file', selectedFile);
    }
    formData.append('chunk_size', chunkSize.toString());
    formData.append('chunk_overlap', chunkOverlap.toString());
    formData.append('split_by_paragraph', splitByParagraph.toString());
    formData.append('split_by_sentence', splitBySentence.toString());
    
    try {
      const response = await axios.post('/api/v1/rag/documents/upload', formData, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
            setUploadProgress(percent);
          }
        }
      });
      
      if (response.data && response.data.success) {
        fetchDocuments();
        setSelectedFile(null);
        setShowPreview(false);
        setSuccessMessage('上传成功');
        
        const fileInput = document.getElementById('file-upload') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
      } else {
        setErrorMessage(response.data.message || '上传失败');
      }
    } catch (error: any) {
      console.error('上传失败:', error);
      setErrorMessage(error.response?.data?.message || '上传失败');
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (id: string) => {
    if (!window.confirm('确定要删除此文档吗？')) return;
    
    try {
      const response = await axios.delete(`/api/v1/rag/documents/${id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.data && response.data.success) {
        setDocuments(docs => docs.filter(doc => doc.id !== id));
        setSuccessMessage('删除成功');
      } else {
        setErrorMessage(response.data.message || '删除失败');
      }
    } catch (error: any) {
      console.error('删除失败:', error);
      setErrorMessage(error.response?.data?.message || '删除失败');
    }
  };

  const handleDeleteCollection = async (collectionId: string, collectionName: string) => {
    setIsDeleting(true);
    setErrorMessage('');
    
    try {
      await documentCollectionApi.deleteCollection(collectionId);
      setCollections(collections => collections.filter(c => c.id !== collectionId));
      setSuccessMessage(`文档集"${collectionName}"已删除`);
    } catch (error: any) {
      console.error('删除文档集失败:', error);
      setErrorMessage(error.response?.data?.message || '删除文档集失败');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/auth');
  };

  const formatDate = (date: Date) => {
    return date.toLocaleString();
  };

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) {
      setErrorMessage('文档集名称不能为空');
      return;
    }

    try {
      const data: DocumentCollectionCreate = {
        name: newCollectionName,
        description: newCollectionDesc,
        tags: newCollectionTags
      };
      
      const response = await documentCollectionApi.createCollection(data);
      if (response.data && response.data.success) {
        setSuccessMessage(response.data.message || '文档集创建成功');
        setShowCollectionDialog(false);
        await fetchCollections();
        
        // 重置表单
        setNewCollectionName('');
        setNewCollectionDesc('');
        setNewCollectionTags([]);
      } else {
        setErrorMessage(response.data?.message || '创建文档集失败');
      }
    } catch (error: any) {
      console.error('创建文档集失败:', error);
      setErrorMessage(error.response?.data?.message || '创建文档集失败，请稍后重试');
    }
  };

  const handleAddToCollection = async (docId: string, collectionId: string) => {
    if (!collectionId) {
      setErrorMessage('请选择文档集');
      return;
    }

    setIsAddingToCollection(true);
    setErrorMessage('');
    
    try {
      await documentCollectionApi.addDocumentToCollection(collectionId, docId);
      setSuccessMessage('文档已添加到文档集');
      fetchCollections();
    } catch (error: any) {
      console.error('添加文档到文档集失败:', error);
      setErrorMessage(error.response?.data?.message || '添加文档到文档集失败');
    } finally {
      setIsAddingToCollection(false);
    }
  };

  const handleRemoveFromCollection = async (collectionId: string, documentId: string) => {
    try {
      await documentCollectionApi.removeDocumentFromCollection(collectionId, documentId);
      setSuccessMessage('文档已从文档集中移除');
      fetchCollections();
      fetchDocuments();
    } catch (error) {
      console.error('从文档集中移除文档失败:', error);
      setErrorMessage('从文档集中移除文档失败');
    }
  };

  const handleDocumentSelect = (docId: string) => {
    setSelectedDocuments(prev => {
      if (prev.includes(docId)) {
        return prev.filter(id => id !== docId);
      }
      return [...prev, docId];
    });
  };

  const handlePreviewSplit = async (docId: string, fileName: string) => {
    setSelectedDocumentId(docId);
    setSelectedDocumentName(fileName);
    setPreviewDialogVisible(true);
    setPreviewLoading(true);
    
    try {
      const response = await axios.get(`/api/v1/rag/documents/${docId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.data && response.data.document) {
        setDocumentSegments(response.data.document.segments || []);
      }
    } catch (error) {
      console.error('获取文档切割预览失败:', error);
      setErrorMessage('获取文档切割预览失败');
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-indigo-600 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-white text-xl font-bold">RAG聊天</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <a href="/chat" className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium">聊天</a>
                <a href="/documents" className="text-white border-indigo-500 px-3 py-2 rounded-md text-sm font-medium border-b-2">文档</a>
                <a href="/models" className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium">模型</a>
              </div>
            </div>
            <div className="flex items-center">
              <button onClick={() => setShowCollectionDialog(true)} className="text-white bg-indigo-500 hover:bg-indigo-600 px-4 py-2 rounded-md text-sm font-medium mr-4">
                创建文档集
              </button>
              <button onClick={() => handleLogout()} className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                退出登录
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">文档集</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {collections.map(collection => (
                <div
                  key={collection.id}
                  onClick={(e) => {
                    // 如果点击的是"查看详情"按钮范围，不触发选中
                    if (!(e.target as HTMLElement).closest('.view-details-btn')) {
                      setSelectedCollections(prev => {
                        if (prev.includes(collection.id)) {
                          return prev.filter(id => id !== collection.id);
                        }
                        return [...prev, collection.id];
                      });
                    }
                  }}
                  className={`relative bg-white rounded-xl shadow-sm transition-all duration-200 hover:shadow-md overflow-hidden cursor-pointer ${
                    selectedCollections.includes(collection.id)
                      ? 'ring-2 ring-indigo-500 bg-indigo-50'
                      : 'hover:ring-1 hover:ring-indigo-300'
                  }`}
                >
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">{collection.name}</h3>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800">
                        {collection.document_count} 文档
                      </span>
                    </div>
                    
                    <div className="text-sm text-gray-600 mb-4">
                      创建于 {new Date(collection.created_at).toLocaleDateString()}
                    </div>

                    {collection.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {collection.tags.map(tag => (
                          <span
                            key={tag}
                            className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
                   <div className="flex justify-between items-center">
                     <button
                       onClick={(e) => {
                         e.stopPropagation();
                         if (window.confirm('确定要删除此文档集吗？此操作无法撤销。')) {
                           handleDeleteCollection(collection.id, collection.name);
                         }
                       }}
                       className="text-sm text-red-600 hover:text-red-800 transition-colors duration-200 disabled:opacity-50"
                       disabled={isDeleting}
                     >
                       {isDeleting ? '删除中...' : '删除'}
                     </button>
                     <button
                       onClick={(e) => {
                         e.stopPropagation();
                         navigate(`/collections/${collection.id}`);
                       }}
                       className="view-details-btn text-sm text-gray-600 hover:text-indigo-600 transition-colors duration-200"
                     >
                       查看详情
                     </button>
                   </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
             <h2 className="text-lg font-semibold text-gray-900">文档管理</h2>
             {selectedDocuments.length > 0 && selectedCollections.length === 1 && (
               <button
                 onClick={() => {
                   Promise.all(
                     selectedDocuments.map(docId =>
                       handleAddToCollection(docId, selectedCollections[0])
                     )
                   );
                 }}
                 disabled={isAddingToCollection}
                 className={`bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium ${
                   isAddingToCollection ? 'opacity-50 cursor-not-allowed' : 'hover:bg-indigo-700'
                 }`}
               >
                 {isAddingToCollection ? '添加中...' : '批量添加到文档集'}
               </button>
             )}
           </div>
            
            {errorMessage && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {errorMessage}
              </div>
            )}
            
            {successMessage && (
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                {successMessage}
              </div>
            )}
            
            <div className="space-y-6">
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">上传新文档</label>
                <div className="space-y-4">
                  <div className="flex items-center space-x-4">
                    <input
                      type="file"
                      accept=".txt,.pdf,.md"
                      onChange={handleFileSelect}
                      disabled={isUploading}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className={`inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white ${
                        isUploading ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 cursor-pointer'
                      }`}
                    >
                      选择文件
                    </label>
                    {selectedFile && (
                      <span className="text-sm text-gray-500">已选择: {selectedFile.name}</span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        块大小 (字符数)
                      </label>
                      <input
                        type="number"
                        value={chunkSize}
                        onChange={(e) => setChunkSize(parseInt(e.target.value))}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        重叠大小 (字符数)
                      </label>
                      <input
                        type="number"
                        value={chunkOverlap}
                        onChange={(e) => setChunkOverlap(parseInt(e.target.value))}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                  </div>

                  <div className="flex items-center space-x-6">
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={splitByParagraph}
                        onChange={(e) => setSplitByParagraph(e.target.checked)}
                        className="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                      />
                      <span className="ml-2 text-sm text-gray-600">按段落分割</span>
                    </label>
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={splitBySentence}
                        onChange={(e) => setSplitBySentence(e.target.checked)}
                        className="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                      />
                      <span className="ml-2 text-sm text-gray-600">按句子分割</span>
                    </label>
                  </div>

                  <div className="flex items-center space-x-4">
                    <button
                      onClick={(e) => handlePreview(e)}
                      disabled={!selectedFile || isUploading}
                      className={`py-2 px-4 border rounded-md shadow-sm text-sm font-medium ${
                        !selectedFile || isUploading
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-white text-indigo-600 hover:bg-indigo-50 border-indigo-600'
                      }`}
                    >
                      预览文档切割
                    </button>
                    <button
                      onClick={handleUpload}
                      disabled={!selectedFile || isUploading}
                      className={`py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                        !selectedFile || isUploading
                          ? 'bg-indigo-400 cursor-not-allowed'
                          : 'bg-indigo-600 hover:bg-indigo-700'
                      }`}
                    >
                      {isUploading ? '上传中...' : '开始上传'}
                    </button>
                  </div>
                </div>
              </div>

              {showPreview && (
                <div className="border-t mt-6 pt-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-4">文档切割预览</h3>
                  <DocumentPreview
                    segments={previewSegments}
                    documentId={previewDocumentId || ''}
                    onClose={() => {
                      setShowPreview(false);
                      setPreviewDocumentId('');
                    }}
                  />
                </div>
              )}

              <div className="mt-8">
                <h3 className="text-sm font-medium text-gray-700 mb-4">上传历史</h3>
                {documents.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    {isUploading ? '正在上传文档...' : '暂无文档，请上传'}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="w-8 px-6 py-3">
                            <input
                              type="checkbox"
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedDocuments(documents.map(doc => doc.id));
                                } else {
                                  setSelectedDocuments([]);
                                }
                              }}
                              checked={selectedDocuments.length === documents.length}
                              className="rounded border-gray-300 text-indigo-600"
                            />
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">文件名</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">上传时间</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">段落数</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {documents.map((doc) => (
                          <tr key={doc.id}>
                            <td className="px-6 py-4">
                              <input
                                type="checkbox"
                                checked={selectedDocuments.includes(doc.id)}
                                onChange={() => handleDocumentSelect(doc.id)}
                                className="rounded border-gray-300 text-indigo-600"
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{doc.file_name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(doc.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.segments_count}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span
                                className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                  doc.status === 'ready'
                                    ? 'bg-green-100 text-green-800'
                                    : doc.status === 'processing'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-red-100 text-red-800'
                                }`}
                              >
                                {doc.status === 'ready' ? '就绪' : doc.status === 'processing' ? '处理中' : '错误'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-4">
                              {selectedCollections.length === 1 && (
                                <button
                                  onClick={async () => {
                                    try {
                                      setErrorMessage('');
                                      const collectionId = selectedCollections[0];
                                      await documentCollectionApi.addDocumentToCollection(collectionId, doc.id);
                                      setSuccessMessage(`文档"${doc.file_name}"已添加到文档集`);
                                      fetchCollections();
                                    } catch (error: any) {
                                      console.error('添加文档到文档集失败:', error);
                                      setErrorMessage(error.response?.data?.message || '添加文档到文档集失败');
                                    }
                                  }}
                                  className="text-indigo-600 hover:text-indigo-900"
                                >
                                  上传到文档集
                                </button>
                              )}
                              <button
                                onClick={() => handlePreviewSplit(doc.id, doc.file_name)}
                                className="text-blue-600 hover:text-blue-900"
                              >
                                查看切割
                              </button>
                              <button
                                onClick={() => deleteDocument(doc.id)}
                                className="text-red-600 hover:text-red-900"
                              >
                                删除
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {showCollectionDialog && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>

            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">创建新文档集</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      名称
                    </label>
                    <input
                      type="text"
                      value={newCollectionName}
                      onChange={(e) => setNewCollectionName(e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      placeholder="输入文档集名称"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      描述
                    </label>
                    <textarea
                      value={newCollectionDesc}
                      onChange={(e) => setNewCollectionDesc(e.target.value)}
                      rows={3}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      placeholder="输入文档集描述"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      标签
                    </label>
                    <input
                      type="text"
                      placeholder="输入标签，按回车添加"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && e.currentTarget.value) {
                          e.preventDefault();
                          setNewCollectionTags([...newCollectionTags, e.currentTarget.value]);
                          e.currentTarget.value = '';
                        }
                      }}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    />
                    {newCollectionTags.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {newCollectionTags.map((tag, index) => (
                          <span
                            key={index}
                            className="bg-gray-100 text-gray-600 text-sm px-2 py-1 rounded flex items-center"
                          >
                            {tag}
                            <button
                              onClick={() => setNewCollectionTags(tags => tags.filter((_, i) => i !== index))}
                              className="ml-1 text-gray-500 hover:text-gray-700"
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleCreateCollection}
                  disabled={!newCollectionName.trim()}
                  className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white sm:ml-3 sm:w-auto sm:text-sm ${
                    newCollectionName.trim()
                      ? 'bg-indigo-600 hover:bg-indigo-700'
                      : 'bg-indigo-400 cursor-not-allowed'
                  }`}
                >
                  创建
                </button>
                <button
                  type="button"
                  onClick={() => setShowCollectionDialog(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 sm:mt-0 sm:w-auto sm:text-sm"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 文档切割预览对话框 */}
      {previewDialogVisible && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-3/4 max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-medium">文档切割预览 - {selectedDocumentName}</h3>
              <button
                onClick={() => setPreviewDialogVisible(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-8rem)]">
              {previewLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                  <span className="ml-2 text-gray-600">加载中...</span>
                </div>
              ) : documentSegments.length > 0 ? (
                <div className="space-y-6">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm text-gray-600">总段落数：{documentSegments.length}</p>
                  </div>
                  
                  {documentSegments.map((segment, index) => (
                    <div key={index} className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-gray-600">段落 #{index + 1}</span>
                        <span className="text-xs text-gray-500">{segment.content.length} 字符</span>
                      </div>
                      <p className="text-gray-800 whitespace-pre-wrap">{segment.content}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  暂无切割数据
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Documents;