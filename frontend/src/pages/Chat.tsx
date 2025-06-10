import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Transition } from '@headlessui/react';
import { getCollections } from '../api/documentCollections';
import { DocumentCollection } from '../types/documentCollection';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  references?: Reference[];
}

interface Reference {
  content: string;
  metadata: {
    doc_id: string;
    document_id: string;
    file_name: string;
    score: number;
  };
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [ragEnabled, setRagEnabled] = useState(true);
  const [showReferences, setShowReferences] = useState<{[key: string]: boolean}>({});
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  
  useEffect(() => {
    // 检查是否已认证
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/auth');
      return;
    }

    // 获取文档集列表
    const fetchCollections = async () => {
      try {
        const response = await getCollections();
        setCollections(response.data);
      } catch (err) {
        console.error('获取文档集失败:', err);
      }
    };

    fetchCollections();
    
    // 滚动到最新消息
    scrollToBottom();
  }, [messages, navigate]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    if (ragEnabled && !selectedCollection) {
      setError('请选择一个文档集');
      return;
    }
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError('');
    
    try {
      const response = await axios.post('/api/v1/rag/chat', {
        query: input,
        enable_rag: ragEnabled,
        top_k: 5,
        conversation_id: "",
        collection_id: ragEnabled ? selectedCollection : undefined
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.data && response.data.success) {
        const assistantMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.data.response,
          timestamp: new Date(),
          references: response.data.sources ? response.data.sources.map((source: any) => ({
            content: source.content,
            metadata: {
              doc_id: "",
              document_id: "",
              file_name: source.file_name,
              score: source.score
            }
          })) : []
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        
        // 初始化引用显示状态
        if (assistantMessage.references && assistantMessage.references.length > 0) {
          setShowReferences(prev => ({
            ...prev,
            [assistantMessage.id]: false
          }));
        }
      } else {
        throw new Error(response.data.message || "回复失败");
      }
    } catch (err) {
      console.error('发送消息失败:', err);
      setError('发送消息失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };
  
  const toggleReferences = (messageId: string) => {
    setShowReferences(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };
  
  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/auth');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* 导航栏 */}
      <nav className="bg-indigo-600 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-white text-xl font-bold">RAG聊天</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <a
                  href="/chat"
                  className="text-white border-indigo-500 px-3 py-2 rounded-md text-sm font-medium border-b-2"
                >
                  聊天
                </a>
                <a
                  href="/documents"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  文档
                </a>
                <a
                  href="/models"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  模型
                </a>
              </div>
            </div>
            <div className="flex items-center">
              <button
                onClick={handleLogout}
                className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
              >
                退出登录
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 聊天区域 */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full p-4">
        {/* 聊天头部 */}
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-medium text-gray-900">聊天助手</h2>
            <div className="flex items-center">
              <span className="mr-2 text-sm text-gray-500">RAG</span>
              <button
                onClick={() => {
                  setRagEnabled(!ragEnabled);
                  if (!ragEnabled) setSelectedCollection('');
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                  ragEnabled ? 'bg-indigo-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    ragEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
          
          {/* 文档集选择器 */}
          {ragEnabled && (
            <div className="flex items-center mt-2">
              <label htmlFor="collection" className="block text-sm font-medium text-gray-700 mr-2">
                文档集
              </label>
              <select
                id="collection"
                value={selectedCollection}
                onChange={(e) => setSelectedCollection(e.target.value)}
                className="flex-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              >
                <option value="">选择文档集</option>
                {collections.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        
        {/* 聊天消息 */}
        <div className="flex-1 overflow-y-auto mb-4 bg-white rounded-lg shadow p-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <svg className="w-12 h-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p>开始与AI助手对话吧</p>
              {ragEnabled && (
                <p className="mt-2 text-sm">
                  已启用RAG功能，AI将参考您的知识库回答问题
                </p>
              )}
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="flex flex-col">
                <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      message.role === 'user'
                        ? 'bg-indigo-100 text-gray-800'
                        : 'bg-white border border-gray-200 text-gray-700'
                    }`}
                  >
                    <div className="text-sm">{message.content}</div>
                    <div className="text-xs text-gray-500 mt-1 text-right">
                      {formatTimestamp(message.timestamp)}
                    </div>
                  </div>
                </div>
                
                {/* 引用资料 */}
                {message.role === 'assistant' && message.references && message.references.length > 0 && (
                  <div className="ml-4 mt-1">
                    <button
                      onClick={() => toggleReferences(message.id)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center"
                    >
                      <svg
                        className={`w-3 h-3 mr-1 transition-transform ${
                          showReferences[message.id] ? 'transform rotate-90' : ''
                        }`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {showReferences[message.id] ? '隐藏引用资料' : `查看引用资料 (${message.references.length})`}
                    </button>
                    
                    <Transition
                      show={showReferences[message.id] || false}
                      enter="transition-opacity duration-75"
                      enterFrom="opacity-0"
                      enterTo="opacity-100"
                      leave="transition-opacity duration-150"
                      leaveFrom="opacity-100"
                      leaveTo="opacity-0"
                    >
                      <div className="mt-2 space-y-2">
                        {message.references.map((ref, index) => (
                          <div key={index} className="bg-gray-50 border border-gray-200 rounded p-2 text-xs">
                            <div className="font-medium text-gray-700 mb-1 flex justify-between">
                              <span>{ref.metadata.file_name}</span>
                              <span className="text-gray-500">
                                相关度: {Math.round(ref.metadata.score * 100)}%
                              </span>
                            </div>
                            <p className="text-gray-600">{ref.content}</p>
                          </div>
                        ))}
                      </div>
                    </Transition>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* 输入区域 */}
        <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
          <div className="flex rounded-md shadow-sm">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
              className="focus:ring-indigo-500 focus:border-indigo-500 flex-1 block w-full rounded-none rounded-l-md sm:text-sm border-gray-300"
              placeholder="输入消息..."
              disabled={isLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !input.trim()}
              className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-r-md text-white ${
                isLoading || !input.trim()
                  ? 'bg-indigo-300 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {isLoading ? (
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat; 