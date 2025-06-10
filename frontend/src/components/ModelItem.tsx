import React from 'react';

interface ModelProps {
  id: string;
  name: string;
  provider: string;
  modelType: string;
  modelCategory?: string;
  isDefault: boolean;
  apiUrl: string;
  onSetDefault: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onTest: (id: string) => void;
}

const ModelItem: React.FC<ModelProps> = ({
  id,
  name,
  provider,
  modelType,
  modelCategory = "chat",
  isDefault,
  apiUrl,
  onSetDefault,
  onEdit,
  onDelete,
  onTest
}) => {
  // 根据模型类别确定标签颜色
  const getCategoryBadge = () => {
    switch(modelCategory) {
      case "embedding":
        return (
          <span className="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
            向量嵌入
          </span>
        );
      case "chat":
        return (
          <span className="ml-2 px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded-full">
            聊天模型
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-4 border-l-4 border-indigo-500">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center flex-wrap">
            <h3 className="text-lg font-medium text-gray-900">{name}</h3>
            {isDefault && (
              <span className="ml-2 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                默认
              </span>
            )}
            {getCategoryBadge()}
          </div>
          <div className="mt-1 text-sm text-gray-500">
            <p><span className="font-medium">提供商:</span> {provider}</p>
            <p><span className="font-medium">模型类型:</span> {modelType}</p>
            <p className="truncate"><span className="font-medium">API地址:</span> {apiUrl}</p>
          </div>
        </div>
        <div className="flex flex-col space-y-2">
          <button
            onClick={() => onTest(id)}
            className="px-3 py-1 text-xs text-indigo-700 hover:text-white border border-indigo-700 hover:bg-indigo-700 rounded transition-colors"
          >
            {modelCategory === "embedding" ? "生成向量" : "测试"}
          </button>
          {!isDefault && (
            <button
              onClick={() => onSetDefault(id)}
              className="px-3 py-1 text-xs text-green-700 hover:text-white border border-green-700 hover:bg-green-700 rounded transition-colors"
            >
              设为默认
            </button>
          )}
        </div>
      </div>
      <div className="mt-4 flex justify-end space-x-2">
        <button
          onClick={() => onEdit(id)}
          className="px-3 py-1 text-xs text-gray-700 hover:text-white border border-gray-700 hover:bg-gray-700 rounded transition-colors"
        >
          编辑
        </button>
        <button
          onClick={() => onDelete(id)}
          className="px-3 py-1 text-xs text-red-700 hover:text-white border border-red-700 hover:bg-red-700 rounded transition-colors"
        >
          删除
        </button>
      </div>
    </div>
  );
};

export default ModelItem; 