import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ModelItem from '../components/ModelItem';
import ModelForm, { ModelFormData } from '../components/ModelForm';
import ModelDiscovery, { DiscoveredModel } from '../components/ModelDiscovery';
import ModelTestDialog from '../components/ModelTestDialog';
import * as api from '../utils/api';

// 导航项接口
interface NavItem {
  id: string;
  name: string;
}

const Models: React.FC = () => {
  // 路由导航
  const navigate = useNavigate();
  
  // 状态变量
  const [models, setModels] = useState<api.LLMModel[]>([]);
  const [providers, setProviders] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('models');
  const [showForm, setShowForm] = useState(false);
  const [editingModel, setEditingModel] = useState<api.LLMModel | null>(null);
  const [testingModel, setTestingModel] = useState<{ id: string; name: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  
  // 导航项
  const navItems: NavItem[] = [
    { id: 'models', name: '模型列表' },
    { id: 'discover', name: '发现模型' },
  ];

  // 加载数据
  useEffect(() => {
    // 检查是否已认证
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/auth');
      return;
    }
    
    fetchModels();
    fetchProviders();
  }, [navigate]);

  // 获取模型列表
  const fetchModels = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const data = await api.getLLMModels();
      setModels(data);
    } catch (error) {
      console.error('获取模型列表失败:', error);
      setError(error instanceof Error ? error.message : '获取模型列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 获取提供商列表
  const fetchProviders = async () => {
    try {
      const data = await api.getLLMProviders();
      setProviders(data);
    } catch (error) {
      console.error('获取提供商列表失败:', error);
    }
  };

  // 处理设置默认模型
  const handleSetDefault = async (id: string) => {
    try {
      setIsLoading(true);
      await api.setDefaultLLMModel(id);
      await fetchModels(); // 重新加载模型列表
    } catch (error) {
      console.error('设置默认模型失败:', error);
      setError(error instanceof Error ? error.message : '设置默认模型失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 处理编辑模型
  const handleEdit = (id: string) => {
    const model = models.find(m => m.id === id);
    if (model) {
      setEditingModel(model);
      setShowForm(true);
    }
  };

  // 处理删除模型
  const handleDelete = async (id: string) => {
    if (confirmDelete !== id) {
      setConfirmDelete(id);
      return;
    }
    
    try {
      setIsLoading(true);
      await api.deleteLLMModel(id);
      setConfirmDelete(null);
      await fetchModels(); // 重新加载模型列表
    } catch (error) {
      console.error('删除模型失败:', error);
      setError(error instanceof Error ? error.message : '删除模型失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 处理测试模型
  const handleTest = (id: string) => {
    const model = models.find(m => m.id === id);
    if (model) {
      setTestingModel({ id, name: model.name });
    }
  };

  // 处理表单提交
  const handleFormSubmit = async (formData: ModelFormData) => {
    try {
      setIsLoading(true);
      
      if (editingModel) {
        // 更新模型
        const updateData: api.UpdateLLMModel = {
          name: formData.name,
          provider: formData.provider,
          model_type: formData.modelType,
          api_url: formData.apiUrl,
          api_key: formData.apiKey,
          description: formData.description,
          context_window: formData.contextWindow,
          max_output_tokens: formData.maxOutputTokens,
          temperature: formData.temperature,
          default: formData.isDefault,
          config: formData.customOptions
        };
        
        await api.updateLLMModel(editingModel.id, updateData);
      } else {
        // 创建新模型
        const createData: api.CreateLLMModel = {
          name: formData.name,
          provider: formData.provider,
          model_type: formData.modelType,
          api_url: formData.apiUrl,
          api_key: formData.apiKey,
          description: formData.description,
          context_window: formData.contextWindow,
          max_output_tokens: formData.maxOutputTokens,
          temperature: formData.temperature,
          default: formData.isDefault,
          config: formData.customOptions
        };
        
        await api.createLLMModel(createData);
      }
      
      setShowForm(false);
      setEditingModel(null);
      await fetchModels(); // 重新加载模型列表
    } catch (error) {
      console.error('保存模型失败:', error);
      setError(error instanceof Error ? error.message : '保存模型失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 处理注册发现的模型
  const handleRegisterModel = async (model: DiscoveredModel) => {
    try {
      setIsLoading(true);
      
      const registerData: api.RegisterDiscoveredModel = {
        llm_model_id: model.id,
        provider: model.provider,
        name: model.name,
        api_url: model.api_url,
        description: model.description,
        context_window: model.context_window
      };
      
      await api.registerDiscoveredModel(registerData);
      await fetchModels(); // 重新加载模型列表
      
      // 注册成功后切换到模型列表标签
      setActiveTab('models');
    } catch (error) {
      console.error('注册模型失败:', error);
      setError(error instanceof Error ? error.message : '注册模型失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 转换编辑模型为表单数据
  const convertModelToFormData = (model: api.LLMModel): ModelFormData => {
    return {
      id: model.id,
      name: model.name,
      provider: model.provider,
      modelType: model.model_type,
      apiUrl: model.api_url,
      apiKey: model.api_key,
      description: model.description || '',
      contextWindow: model.context_window,
      maxOutputTokens: model.max_output_tokens,
      temperature: model.temperature,
      isDefault: model.default,
      customOptions: model.config
    };
  };

  return (
    <div className="min-h-screen bg-gray-100">
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
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
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
                  className="text-white border-indigo-500 px-3 py-2 rounded-md text-sm font-medium border-b-2"
                >
                  模型
                </a>
              </div>
            </div>
            <div className="flex items-center">
              <button
                onClick={() => {
                  localStorage.removeItem('token');
                  navigate('/auth');
                }}
                className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
              >
                退出登录
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="border-b border-gray-200">
            <div className="flex justify-between items-center mb-4">
              <h1 className="text-2xl font-bold text-gray-900">模型管理</h1>
              {activeTab === 'models' && !showForm && (
                <button
                  onClick={() => {
                    setEditingModel(null);
                    setShowForm(true);
                  }}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  添加新模型
                </button>
              )}
            </div>
            
            {/* 标签页切换 */}
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex" aria-label="Tabs">
                {navItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`
                      w-1/2 py-4 px-1 text-center border-b-2 font-medium text-sm
                      ${activeTab === item.id
                        ? 'border-indigo-500 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                    `}
                  >
                    {item.name}
                  </button>
                ))}
              </nav>
            </div>
          </div>
          
          {/* 错误提示 */}
          {error && (
            <div className="mt-4 bg-red-50 border-l-4 border-red-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">
                    {error}
                  </p>
                </div>
                <div className="ml-auto pl-3">
                  <div className="-mx-1.5 -my-1.5">
                    <button
                      onClick={() => setError('')}
                      className="inline-flex rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div className="mt-6">
            {/* 模型列表标签页 */}
            {activeTab === 'models' && !showForm && (
              <div className="space-y-6">
                {isLoading && models.length === 0 ? (
                  <div className="text-center py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p className="mt-2 text-gray-500">加载中...</p>
                  </div>
                ) : models.length === 0 ? (
                  <div className="text-center py-12 bg-white rounded-lg shadow">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">没有模型</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      您还没有添加任何模型，请点击添加按钮创建一个新模型。
                    </p>
                    <div className="mt-6">
                      <button
                        onClick={() => {
                          setEditingModel(null);
                          setShowForm(true);
                        }}
                        className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        添加新模型
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    {models.map((model) => (
                      <ModelItem
                        key={model.id}
                        id={model.id}
                        name={model.name}
                        provider={model.provider}
                        modelType={model.model_type}
                        modelCategory={model.model_category}
                        isDefault={model.default}
                        apiUrl={model.api_url}
                        onSetDefault={handleSetDefault}
                        onEdit={handleEdit}
                        onDelete={
                          confirmDelete === model.id
                          ? () => handleDelete(model.id)
                          : () => setConfirmDelete(model.id)
                        }
                        onTest={handleTest}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* 模型表单 */}
            {activeTab === 'models' && showForm && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-6">
                  {editingModel ? '编辑模型' : '添加新模型'}
                </h2>
                <ModelForm
                  initialData={editingModel ? convertModelToFormData(editingModel) : undefined}
                  providers={providers}
                  onSubmit={handleFormSubmit}
                  onCancel={() => {
                    setShowForm(false);
                    setEditingModel(null);
                  }}
                  isSubmitting={isLoading}
                />
              </div>
            )}
            
            {/* 发现模型标签页 */}
            {activeTab === 'discover' && (
              <ModelDiscovery
                onRegisterModel={handleRegisterModel}
                isLoading={isLoading}
              />
            )}
          </div>
        </div>
      </div>
      
      {/* 模型测试对话框 */}
      {testingModel && (
        <ModelTestDialog
          modelId={testingModel.id}
          modelName={testingModel.name}
          isOpen={true}
          onClose={() => setTestingModel(null)}
        />
      )}
    </div>
  );
};

export default Models; 