import React, { useState } from 'react';
import * as api from '../utils/api';

export interface DiscoveredModel {
  id: string;
  name: string;
  provider: string;
  is_registered: boolean;
  api_url: string;
  context_window: number;
  description: string;
}

interface ModelDiscoveryProps {
  onRegisterModel: (model: DiscoveredModel) => void;
  isLoading: boolean;
}

const ModelDiscovery: React.FC<ModelDiscoveryProps> = ({ onRegisterModel, isLoading }) => {
  const [provider, setProvider] = useState('lmstudio');
  const [apiUrl, setApiUrl] = useState('http://localhost:1234');
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [discoveredModels, setDiscoveredModels] = useState<api.DiscoveredModel[]>([]);
  const [error, setError] = useState('');

  const handleDiscover = async () => {
    if (!apiUrl) {
      setError('请输入API URL');
      return;
    }

    setDiscoveryLoading(true);
    setError('');

    try {
      const data = await api.discoverModels(provider, apiUrl);
      setDiscoveredModels(data);

      if (data.length === 0) {
        setError('未发现任何模型');
      }
    } catch (error) {
      console.error('模型发现错误:', error);
      setError(error instanceof Error ? error.message : '发现模型时出错');
    } finally {
      setDiscoveryLoading(false);
    }
  };

  const handleModelRegister = (model: api.DiscoveredModel) => {
    const convertedModel: DiscoveredModel = {
      id: model.id,
      name: model.name,
      provider: model.provider,
      is_registered: model.is_registered,
      api_url: model.api_url,
      context_window: model.context_window,
      description: model.description
    };
    
    onRegisterModel(convertedModel);
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-medium text-gray-900 mb-4">发现本地模型</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label htmlFor="provider" className="block text-sm font-medium text-gray-700 mb-1">
            提供商
          </label>
          <select
            id="provider"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="lmstudio">LM Studio</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>
        
        <div>
          <label htmlFor="apiUrl" className="block text-sm font-medium text-gray-700 mb-1">
            API URL
          </label>
          <input
            type="text"
            id="apiUrl"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder={provider === 'lmstudio' ? 'http://localhost:1234' : 'http://localhost:11434'}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>
        
        <div className="flex items-end">
          <button
            onClick={handleDiscover}
            disabled={discoveryLoading}
            className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {discoveryLoading ? '发现中...' : '发现模型'}
          </button>
        </div>
      </div>
      
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}
      
      {discoveredModels.length > 0 && (
        <div>
          <h3 className="text-md font-medium text-gray-900 mb-2">发现的模型</h3>
          <div className="border rounded-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    模型名称
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    提供商
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {discoveredModels.map((model) => (
                  <tr key={model.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {model.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {model.provider}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {model.is_registered ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          已注册
                        </span>
                      ) : (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                          未注册
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleModelRegister(model)}
                        disabled={model.is_registered || isLoading}
                        className={`text-indigo-600 hover:text-indigo-900 ${model.is_registered ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        {model.is_registered ? '已注册' : '注册'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelDiscovery; 