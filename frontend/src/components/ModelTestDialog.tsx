import React, { useState, useEffect } from 'react';

interface ModelTestDialogProps {
  modelId: string;
  modelName: string;
  isOpen: boolean;
  onClose: () => void;
}

const ModelTestDialog: React.FC<ModelTestDialogProps> = ({
  modelId,
  modelName,
  isOpen,
  onClose
}) => {
  const [prompt, setPrompt] = useState('你好，请自我介绍一下。');
  const [response, setResponse] = useState('');
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState('');
  const [isEmbedding, setIsEmbedding] = useState(false);

  useEffect(() => {
    // 检测模型名称中是否包含"embedding"关键词
    if (modelName.toLowerCase().includes('embedding')) {
      setIsEmbedding(true);
      setPrompt('这是一段用于生成向量嵌入的文本。');
    } else {
      setIsEmbedding(false);
      setPrompt('你好，请自我介绍一下。');
    }
  }, [modelName]);

  if (!isOpen) return null;

  const handleTest = async () => {
    if (!prompt.trim()) {
      setError('请输入测试提示语');
      return;
    }

    setIsTesting(true);
    setError('');
    setResponse('');

    try {
      const response = await fetch('/api/v1/llm/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          llm_id: modelId,
          prompt: prompt
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '测试失败');
      }

      const data = await response.json();
      
      // 处理不同格式的响应
      let content = '';
      if (data.choices && data.choices[0] && data.choices[0].message) {
        // OpenAI格式
        content = data.choices[0].message.content;
      } else if (data.response) {
        // Ollama格式
        content = data.response;
      } else if (data.message) {
        // 通用格式
        content = data.message;
      } else if (data.data && Array.isArray(data.data) && data.data[0]?.embedding) {
        // Embedding响应格式
        const embedding = data.data[0].embedding;
        // 只显示前10个元素和最后10个元素，以避免显示过多
        const firstPart = embedding.slice(0, 10);
        const lastPart = embedding.slice(-10);
        content = `模型生成了 ${embedding.length} 维的向量表示。\n\n前10个元素:\n${JSON.stringify(firstPart, null, 2)}\n\n...\n\n最后10个元素:\n${JSON.stringify(lastPart, null, 2)}`;
      } else if (data.embedding || (data.data && data.data.embedding)) {
        // 其他格式的Embedding响应
        const embedding = data.embedding || data.data.embedding;
        // 如果是数组，同样只显示部分
        if (Array.isArray(embedding)) {
          const firstPart = embedding.slice(0, 10);
          const lastPart = embedding.slice(-10);
          content = `模型生成了 ${embedding.length} 维的向量表示。\n\n前10个元素:\n${JSON.stringify(firstPart, null, 2)}\n\n...\n\n最后10个元素:\n${JSON.stringify(lastPart, null, 2)}`;
        } else {
          content = `Embedding响应: ${JSON.stringify(embedding, null, 2)}`;
        }
      } else {
        // 原始响应
        content = JSON.stringify(data, null, 2);
      }
      
      setResponse(content);
    } catch (error) {
      console.error('测试模型错误:', error);
      setError(error instanceof Error ? error.message : '测试模型时出错');
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col">
        <div className="p-4 border-b">
          <h2 className="text-lg font-medium text-gray-900">
            测试模型: {modelName}
            {isEmbedding && <span className="ml-2 text-sm bg-blue-100 text-blue-800 px-2 py-0.5 rounded">Embedding模型</span>}
          </h2>
        </div>

        <div className="p-4 flex-grow overflow-auto">
          <div className="mb-4">
            <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-1">
              {isEmbedding ? '文本输入' : '测试提示语'}
            </label>
            <textarea
              id="prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              placeholder={isEmbedding ? "输入要转换为向量的文本..." : "输入测试提示语..."}
            />
            {isEmbedding && (
              <p className="mt-1 text-xs text-gray-500">
                Embedding模型会将输入文本转换为向量表示，用于相似度比较、聚类等任务。
              </p>
            )}
          </div>

          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">
                {isEmbedding ? '向量表示' : '模型响应'}
              </label>
              {isTesting && (
                <span className="text-xs text-gray-500 animate-pulse">
                  处理中...
                </span>
              )}
            </div>
            <div className="bg-gray-50 rounded-md p-3 min-h-[150px] border border-gray-200">
              {response ? (
                <pre className="whitespace-pre-wrap text-sm">{response}</pre>
              ) : error ? (
                <div className="text-red-600 text-sm">{error}</div>
              ) : (
                <div className="text-gray-400 text-sm">
                  {isEmbedding ? '向量数据将显示在这里' : '响应将显示在这里'}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="p-4 border-t flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            关闭
          </button>
          <button
            onClick={handleTest}
            disabled={isTesting}
            className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {isTesting ? '测试中...' : isEmbedding ? '生成向量' : '运行测试'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelTestDialog; 