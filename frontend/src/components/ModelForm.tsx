import React, { useState, useEffect } from 'react';

export interface ModelFormData {
  id?: string;
  name: string;
  provider: string;
  modelType: string;
  apiUrl: string;
  apiKey?: string;
  description: string;
  contextWindow: number;
  maxOutputTokens: number;
  temperature: number;
  isDefault: boolean;
  customOptions?: Record<string, any>;
}

interface ModelFormProps {
  initialData?: ModelFormData;
  providers: string[];
  onSubmit: (data: ModelFormData) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

const defaultFormData: ModelFormData = {
  name: '',
  provider: '',
  modelType: '',
  apiUrl: '',
  apiKey: '',
  description: '',
  contextWindow: 8192,
  maxOutputTokens: 1000,
  temperature: 0.7,
  isDefault: false,
  customOptions: {}
};

const ModelForm: React.FC<ModelFormProps> = ({
  initialData,
  providers,
  onSubmit,
  onCancel,
  isSubmitting
}) => {
  const [formData, setFormData] = useState<ModelFormData>(initialData || defaultFormData);
  const [customOptionKey, setCustomOptionKey] = useState('');
  const [customOptionValue, setCustomOptionValue] = useState('');
  const [showCustomOptions, setShowCustomOptions] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData(initialData);
      if (initialData.customOptions && Object.keys(initialData.customOptions).length > 0) {
        setShowCustomOptions(true);
      }
    }
  }, [initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : 
              type === 'checkbox' ? (e.target as HTMLInputElement).checked : 
              value
    }));
  };

  const handleAddCustomOption = () => {
    if (!customOptionKey.trim()) return;
    
    try {
      // 尝试解析值（可能是数字、布尔值或JSON对象）
      let parsedValue: any = customOptionValue;
      try {
        parsedValue = JSON.parse(customOptionValue);
      } catch {
        // 如果不是有效的JSON，保持字符串值
      }
      
      setFormData(prev => ({
        ...prev,
        customOptions: {
          ...(prev.customOptions || {}),
          [customOptionKey]: parsedValue
        }
      }));
      
      setCustomOptionKey('');
      setCustomOptionValue('');
    } catch (error) {
      alert('无效的JSON格式');
    }
  };

  const handleRemoveCustomOption = (key: string) => {
    setFormData(prev => {
      const updatedOptions = { ...(prev.customOptions || {}) };
      delete updatedOptions[key];
      return {
        ...prev,
        customOptions: updatedOptions
      };
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
            显示名称 *
          </label>
          <input
            type="text"
            name="name"
            id="name"
            required
            value={formData.name}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="provider" className="block text-sm font-medium text-gray-700">
            提供商 *
          </label>
          <select
            name="provider"
            id="provider"
            required
            value={formData.provider}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="">选择提供商</option>
            {providers.map(provider => (
              <option key={provider} value={provider}>
                {provider}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="modelType" className="block text-sm font-medium text-gray-700">
            模型类型 *
          </label>
          <input
            type="text"
            name="modelType"
            id="modelType"
            required
            value={formData.modelType}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="apiUrl" className="block text-sm font-medium text-gray-700">
            API URL *
          </label>
          <input
            type="text"
            name="apiUrl"
            id="apiUrl"
            required
            value={formData.apiUrl}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700">
            API Key
          </label>
          <input
            type="password"
            name="apiKey"
            id="apiKey"
            value={formData.apiKey || ''}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="contextWindow" className="block text-sm font-medium text-gray-700">
            上下文窗口大小
          </label>
          <input
            type="number"
            name="contextWindow"
            id="contextWindow"
            min="1"
            value={formData.contextWindow}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="maxOutputTokens" className="block text-sm font-medium text-gray-700">
            最大输出Token数
          </label>
          <input
            type="number"
            name="maxOutputTokens"
            id="maxOutputTokens"
            min="1"
            value={formData.maxOutputTokens}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="temperature" className="block text-sm font-medium text-gray-700">
            温度
          </label>
          <input
            type="number"
            name="temperature"
            id="temperature"
            min="0"
            max="2"
            step="0.1"
            value={formData.temperature}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div className="col-span-1 md:col-span-2">
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">
            模型描述
          </label>
          <textarea
            name="description"
            id="description"
            rows={3}
            value={formData.description}
            onChange={handleChange}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div className="col-span-1 md:col-span-2">
          <div className="flex items-center">
            <input
              type="checkbox"
              name="isDefault"
              id="isDefault"
              checked={formData.isDefault}
              onChange={handleChange}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="isDefault" className="ml-2 block text-sm text-gray-700">
              设为默认模型
            </label>
          </div>
        </div>

        <div className="col-span-1 md:col-span-2">
          <button
            type="button"
            onClick={() => setShowCustomOptions(!showCustomOptions)}
            className="text-sm text-indigo-600 hover:text-indigo-900"
          >
            {showCustomOptions ? '隐藏' : '显示'}自定义选项
          </button>
          
          {showCustomOptions && (
            <div className="mt-3 border rounded-md p-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">自定义选项</h4>
              
              {formData.customOptions && Object.keys(formData.customOptions).length > 0 && (
                <div className="mb-4 space-y-2">
                  {Object.entries(formData.customOptions).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                      <div>
                        <span className="font-medium">{key}:</span>{' '}
                        <span className="text-gray-600">{JSON.stringify(value)}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveCustomOption(key)}
                        className="text-red-600 hover:text-red-900 text-sm"
                      >
                        删除
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-1">
                  <input
                    type="text"
                    placeholder="键名"
                    value={customOptionKey}
                    onChange={(e) => setCustomOptionKey(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <input
                    type="text"
                    placeholder="值"
                    value={customOptionValue}
                    onChange={(e) => setCustomOptionValue(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <button
                    type="button"
                    onClick={handleAddCustomOption}
                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    添加
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                提示: 值可以是字符串、数字、布尔值或JSON对象
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          className="py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isSubmitting ? '提交中...' : '保存'}
        </button>
      </div>
    </form>
  );
};

export default ModelForm; 