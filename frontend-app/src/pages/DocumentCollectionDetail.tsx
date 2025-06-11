import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import DocumentPreview from '../components/DocumentPreview';
import { DocumentCollection } from '../types/documentCollection';
import { Document, PreviewSegment } from '../utils/types';
import * as documentCollectionApi from '../api/documentCollections';

const DocumentCollectionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [collection, setCollection] = useState<DocumentCollection | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/auth');
      return;
    }
    
    if (id) {
      fetchCollectionDetails();
    }
  }, [id, navigate]);
  
  const fetchCollectionDetails = async () => {
    if (!id) return;

    setLoading(true);
    setError('');

    try {
      // 先获取文档集信息
      const collectionResponse = await documentCollectionApi.getCollection(id);
      setCollection(collectionResponse.data.collection);

      try {
        // 再获取文档列表
        const documentsResponse = await documentCollectionApi.getCollectionDocuments(id);
        setDocuments(documentsResponse.data.documents.map((doc: any) => ({
          ...doc,
          created_at: new Date(doc.created_at)
        })));
      } catch (docError: any) {
        // 单独处理文档列表获取失败的情况
        console.error('获取文档列表失败:', docError);
        setError(docError.response?.data?.detail || docError.response?.data?.message || '获取文档列表失败');
      }
    } catch (error: any) {
      // 处理文档集获取失败的情况
      console.error('获取文档集详情失败:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || '获取文档集详情失败';
      setError(`文档集获取失败：${errorMessage}`);
      setCollection(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !collection) return;

    try {
      setUploading(true);
      setError('');
      
      // 创建 FormData
      const formData = new FormData();
      formData.append('file', file);
      formData.append('chunk_size', '512');
      formData.append('chunk_overlap', '50');
      formData.append('split_by_paragraph', 'true');
      formData.append('split_by_sentence', 'true');

      // 上传文件
      const response = await fetch('/api/v1/rag/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.message || '上传失败');
      }

      // 如果上传成功，将文档添加到文档集
      if (result.success && result.doc_id) {
        await documentCollectionApi.addDocumentToCollection(collection.id, result.doc_id);
        setSuccessMessage('文档上传并添加成功');
        // 刷新文档列表
        const documentsResponse = await documentCollectionApi.getCollectionDocuments(collection.id);
        setDocuments(documentsResponse.data.documents.map((doc: any) => ({
          ...doc,
          created_at: new Date(doc.created_at)
        })));
      }
    } catch (error: any) {
      console.error('上传文档失败:', error);
      setError(error.message || '上传文档失败');
    } finally {
      setUploading(false);
      // 3秒后清除成功消息
      if (successMessage) {
        setTimeout(() => setSuccessMessage(''), 3000);
      }
    }
  };

  const handleRemoveDocument = async (documentId: string) => {
    if (!collection || !window.confirm('确定要从文档集中移除此文档吗？')) return;
    
    try {
      await documentCollectionApi.removeDocumentFromCollection(collection.id, documentId);
      setSuccessMessage('文档已从文档集中移除');
      setDocuments(docs => docs.filter(doc => doc.id !== documentId));
    } catch (error: any) {
      console.error('移除文档失败:', error);
      setError(error.response?.data?.message || '移除文档失败');
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">出错了</div>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => navigate('/documents')}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            返回文档页面
          </button>
        </div>
      </div>
    );
  }

  if (!collection) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-600 text-xl mb-4">未找到文档集</div>
          <button
            onClick={() => navigate('/documents')}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            返回文档页面
          </button>
        </div>
      </div>
    );
  }

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
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* 文档集信息 */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{collection.name}</h2>
                {collection.description && (
                  <p className="text-gray-600 mb-4">{collection.description}</p>
                )}
                <div className="text-sm text-gray-500">
                  创建于 {new Date(collection.created_at).toLocaleString()}
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <label className="px-4 py-2 border border-indigo-500 rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 cursor-pointer">
                  <span>{uploading ? '上传中...' : '添加文档'}</span>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.txt,.md"
                    onChange={handleFileUpload}
                    disabled={uploading}
                  />
                </label>
                <button
                  onClick={() => navigate('/documents')}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  返回列表
                </button>
              </div>
            </div>

            {collection.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {collection.tags.map(tag => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 文档列表 */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                文档列表 ({documents.length})
              </h3>
            </div>

            {successMessage && (
              <div className="m-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
                {successMessage}
              </div>
            )}

            {documents.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                该文档集还没有任何文档
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        文档名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        上传时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {documents.map((doc) => (
                      <tr key={doc.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {doc.file_name}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">
                            {doc.created_at.toLocaleString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button
                            onClick={() => handleRemoveDocument(doc.id)}
                            className="text-red-600 hover:text-red-900 mr-4"
                          >
                            移除
                          </button>
                          <a
                            href={`/api/v1/rag/documents/${doc.id}/download`}
                            className="text-indigo-600 hover:text-indigo-900"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            下载
                          </a>
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
  );
};

export default DocumentCollectionDetail;