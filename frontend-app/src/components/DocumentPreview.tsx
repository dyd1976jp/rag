import React, { useState, useCallback, useEffect } from 'react';
import {
  getDocumentSlicePreview,
  getDocumentSplitterParams
} from '../api/documentCollections';

/**
 * DocumentPreview 组件 - 段落详情预览组件
 *
 * 职责：专门用于显示单个段落的详细信息
 * - 显示段落列表供用户选择
 * - 调用段落预览API获取特定段落的父子内容关系
 * - 展示选中段落的详细信息（父内容 + 子内容列表）
 *
 * 注意：此组件不用于完整文档预览，完整文档预览请使用 CompleteDocumentPreview 组件
 */

interface SplitterParams {
  chunkSize: number;
  chunkOverlap: number;
  minChunkSize: number;
  splitByParagraph: boolean;
  paragraphSeparator: string;
  splitBySentence: boolean;
}

interface PreviewSegment {
  id: number;
  content: string;
  start: number;
  end: number;
  length: number;
}

interface DocumentPreviewProps {
  segments: PreviewSegment[];
  documentId: string;
  onClose: () => void;
  initialSegmentId?: number; // 初始选中的段落ID
}

interface PreviewData {
  parentContent: string;
  childrenContent: string[];
}

interface PreviewState {
  data: PreviewData | null;
  isLoading: boolean;
  error: string | null;
  retryCount: number;
}

const MAX_RETRY_COUNT = 3;
const RETRY_DELAY = 1000; // 1秒

const DocumentPreview: React.FC<DocumentPreviewProps> = ({ segments, documentId, onClose, initialSegmentId }) => {
  // 添加切割参数状态
  const [splitterParams, setSplitterParams] = useState<SplitterParams>({
    chunkSize: 512,
    chunkOverlap: 50,
    minChunkSize: 50,
    splitByParagraph: true,
    paragraphSeparator: "\\n\\n",
    splitBySentence: true
  });

  // 加载文档切割参数
  useEffect(() => {
    const loadSplitterParams = async () => {
      try {
        console.log('正在加载文档切割参数:', documentId);

        // 检查是否为预览模式的文档
        if (documentId.startsWith('preview_')) {
          console.log('检测到预览模式文档，使用默认切割参数');
          // 对于预览模式的文档，使用默认参数，避免不必要的API调用
          setSplitterParams({
            chunkSize: 512,
            chunkOverlap: 50,
            minChunkSize: 50,
            splitByParagraph: true,
            paragraphSeparator: "\\n\\n",
            splitBySentence: true
          });
          return;
        }

        const params = await getDocumentSplitterParams(documentId);
        console.log('获取到切割参数:', params);
        setSplitterParams({
          chunkSize: params.chunk_size,
          chunkOverlap: params.chunk_overlap,
          minChunkSize: params.min_chunk_size,
          splitByParagraph: params.split_by_paragraph,
          paragraphSeparator: params.paragraph_separator,
          splitBySentence: params.split_by_sentence
        });
      } catch (error) {
        console.error('加载切割参数失败:', error);
        // 保持默认参数值
      }
    };

    if (documentId) {
      loadSplitterParams();
    }
  }, [documentId]);

  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);
  const [previewState, setPreviewState] = useState<PreviewState>({
    data: null,
    isLoading: false,
    error: null,
    retryCount: 0
  });

  const loadPreviewWithRetry = useCallback(async (segmentId: number, retryAttempt = 0) => {
    // 在开始加载之前验证documentId
    if (!documentId) {
      console.warn('DocumentPreview: 未提供文档ID');
      setPreviewState(prev => ({
        ...prev,
        isLoading: false,
        error: '请先选择要预览的文档',
        data: null
      }));
      return;
    }

    setPreviewState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
      data: null
    }));

    try {
      console.log('开始加载切片预览:', {
        documentId,
        segmentId,
        retryAttempt,
        isPreviewMode: documentId.startsWith('preview_')
      });

      if (typeof segmentId !== 'number' || segmentId < 0) {
        throw new Error('无效的切片索引');
      }

      const preview = await getDocumentSlicePreview(documentId, segmentId);
      console.log('获取到切片预览数据:', {
        success: preview.success,
        hasParentContent: !!preview.parentContent,
        parentContentLength: preview.parentContent?.length || 0,
        childrenCount: preview.childrenContent?.length || 0
      });

      // 检查API响应是否成功
      if (!preview.success) {
        const errorMsg = preview.message || '获取预览数据失败';
        console.error('API响应失败:', errorMsg);
        throw new Error(errorMsg);
      }

      // 验证返回的数据
      if (!preview.parentContent && !preview.childrenContent?.length) {
        console.warn('API返回的预览数据为空:', preview);
        throw new Error('未获取到有效的预览内容，可能是预览数据已过期或段落不存在');
      }

      setPreviewState({
        data: {
          parentContent: preview.parentContent || '',
          childrenContent: preview.childrenContent || []
        },
        isLoading: false,
        error: null,
        retryCount: 0
      });
    } catch (error: any) {
      console.error('加载预览失败:', error);

      // 特殊处理预览模式的错误
      let errorMessage = error.message || '未知错误';
      if (documentId.startsWith('preview_') && errorMessage.includes('预览文档不存在或已过期')) {
        errorMessage = '预览数据已过期，请重新生成文档预览';
      }

      // 如果还有重试次数，则进行重试
      if (retryAttempt < MAX_RETRY_COUNT && !errorMessage.includes('预览数据已过期')) {
        console.log(`第 ${retryAttempt + 1} 次重试...`);

        // 使用指数退避策略进行重试
        const delay = RETRY_DELAY * Math.pow(2, retryAttempt);
        setTimeout(() => {
          loadPreviewWithRetry(segmentId, retryAttempt + 1);
        }, delay);
      } else {
        setPreviewState(prev => ({
          ...prev,
          isLoading: false,
          error: `加载失败: ${errorMessage}`,
          retryCount: retryAttempt
        }));
      }
    }
  }, [documentId]);

  const handleSegmentClick = useCallback(async (segmentId: number) => {
    console.log('点击段落:', {
      segmentId,
      currentSelected: selectedSegment,
      hasError: !!previewState.error
    });

    if (selectedSegment === segmentId && !previewState.error) {
      console.log('跳过重复加载相同段落');
      return;
    }
    
    setSelectedSegment(segmentId);
    await loadPreviewWithRetry(segmentId);
  }, [selectedSegment, previewState.error, loadPreviewWithRetry]);

  // 组件挂载时验证props并自动选择初始段落
  useEffect(() => {
    if (!documentId) {
      console.error('DocumentPreview: documentId不能为空');
    }

    // 如果指定了初始段落ID，自动选择并加载
    if (initialSegmentId !== undefined && initialSegmentId !== null) {
      console.log('自动选择初始段落:', initialSegmentId);
      handleSegmentClick(initialSegmentId);
    }
  }, [documentId, initialSegmentId, handleSegmentClick]);

  return (
    <div className="mt-6">
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-900">
              段落详情预览（共 {segments.length} 个段落）
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500"
            >
              <span className="sr-only">关闭</span>
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* 切割参数显示 */}
          <div className="bg-gray-50 rounded-lg p-3 grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">块大小：</span>
              <span className="font-medium">{splitterParams.chunkSize}</span>
              <span className="text-gray-400 ml-1">字符</span>
            </div>
            <div>
              <span className="text-gray-500">重叠大小：</span>
              <span className="font-medium">{splitterParams.chunkOverlap}</span>
              <span className="text-gray-400 ml-1">字符</span>
            </div>
            <div>
              <span className="text-gray-500">最小块大小：</span>
              <span className="font-medium">{splitterParams.minChunkSize}</span>
              <span className="text-gray-400 ml-1">字符</span>
            </div>
            <div>
              <span className="text-gray-500">按段落分割：</span>
              <span className="font-medium">{splitterParams.splitByParagraph ? '是' : '否'}</span>
            </div>
            <div>
              <span className="text-gray-500">段落分隔符：</span>
              <span className="font-medium font-mono">{splitterParams.paragraphSeparator}</span>
            </div>
            <div>
              <span className="text-gray-500">按句子分割：</span>
              <span className="font-medium">{splitterParams.splitBySentence ? '是' : '否'}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-4 p-4">
          {/* 左侧段落列表 */}
          <div className="col-span-2 border-r pr-4 max-h-[600px] overflow-y-auto">
            <div className="space-y-2">
              {segments.map((segment) => (
                <div
                  key={segment.id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors
                    ${selectedSegment === segment.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'hover:bg-gray-50'
                    }`}
                  onClick={() => handleSegmentClick(segment.id)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-500">
                      段落 {segment.id + 1}
                    </span>
                    <span className="text-xs text-gray-400">
                      {segment.length} 字符
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 line-clamp-2">
                    {segment.content}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 右侧预览内容 */}
          <div className="col-span-3 pl-4">
            <div className="bg-white rounded-lg border p-4 max-h-[600px] overflow-y-auto">
              {previewState.isLoading ? (
                <div className="flex flex-col items-center justify-center h-[400px]">
                  <div className="animate-spin rounded-full h-10 w-10 border-3 border-blue-500 border-t-transparent mb-4" />
                  <p className="text-sm text-gray-500">加载预览内容中...</p>
                </div>
              ) : previewState.error ? (
                <div className="flex flex-col items-center justify-center h-[400px]">
                  <div className="text-red-500 mb-4 text-center max-w-md">
                    <svg className="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div className="text-base mb-2">{previewState.error}</div>
                    {previewState.error.includes('预览数据已过期') && (
                      <div className="text-sm text-gray-600">
                        请返回上传页面重新生成文档预览
                      </div>
                    )}
                  </div>
                  <div className="flex gap-3">
                    {previewState.retryCount < MAX_RETRY_COUNT &&
                     selectedSegment !== null &&
                     documentId &&
                     !previewState.error.includes('预览数据已过期') && (
                      <button
                        onClick={() => handleSegmentClick(selectedSegment)}
                        className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                      >
                        重新加载
                      </button>
                    )}
                    <button
                      onClick={onClose}
                      className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                    >
                      关闭预览
                    </button>
                  </div>
                </div>
              ) : selectedSegment === null ? (
                <div className="flex items-center justify-center h-[400px] text-gray-500">
                  <div className="text-center">
                    <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 616 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <p>请选择左侧段落查看详细信息</p>
                    <p className="text-xs text-gray-400 mt-2">此组件专门用于查看单个段落的父子内容关系</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* 父切片内容 */}
                  <div className="bg-gray-50 rounded-lg p-4 border">
                    <div className="flex justify-between items-center mb-3">
                      <h3 className="text-sm font-medium text-gray-900">父级内容</h3>
                      {previewState.data?.parentContent && (
                        <span className="text-xs text-gray-500">
                          {previewState.data.parentContent.length} 字符
                        </span>
                      )}
                    </div>
                    <div className="bg-white rounded p-3 border">
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {previewState.data?.parentContent || '无父级内容'}
                      </p>
                    </div>
                  </div>

                  {/* 子切片内容列表 */}
                  {previewState.data?.childrenContent && previewState.data.childrenContent.length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-4 border">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="text-sm font-medium text-gray-900">子切片内容</h3>
                        <span className="text-xs text-gray-500">
                          {previewState.data.childrenContent.length} 个切片
                        </span>
                      </div>
                      <div className="space-y-3">
                        {previewState.data.childrenContent.map((content, index) => (
                          <div key={index} className="bg-white rounded p-3 border">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-xs font-medium text-gray-500">切片 {index + 1}</span>
                              <span className="text-xs text-gray-400">{content.length} 字符</span>
                            </div>
                            <p className="text-sm text-gray-700 whitespace-pre-wrap">{content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentPreview; 