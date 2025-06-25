import React, { useState, useCallback } from 'react';
import { getCompleteDocumentPreview, CompleteDocumentPreviewResponse, ParentSegment, ChildSegment } from '../api/documentCollections';

interface CompleteDocumentPreviewProps {
  file: File | null;
  chunkSize: number;
  chunkOverlap: number;
  splitByParagraph: boolean;
  splitBySentence: boolean;
  onClose: () => void;
  onSegmentClick?: (segmentId: number) => void;
  onPreviewDataReady?: (docId: string, segments: any[]) => void;
}

interface PreviewState {
  data: CompleteDocumentPreviewResponse | null;
  isLoading: boolean;
  error: string | null;
  debugInfo: {
    requestParams: any;
    rawResponse: any;
    responseHeaders: any;
  } | null;
}

const CompleteDocumentPreview: React.FC<CompleteDocumentPreviewProps> = ({
  file,
  chunkSize,
  chunkOverlap,
  splitByParagraph,
  splitBySentence,
  onClose,
  onSegmentClick,
  onPreviewDataReady
}) => {
  const [previewState, setPreviewState] = useState<PreviewState>({
    data: null,
    isLoading: false,
    error: null,
    debugInfo: null
  });

  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);
  const [showDebugInfo, setShowDebugInfo] = useState<boolean>(false);
  const [expandedParents, setExpandedParents] = useState<Set<number>>(new Set());

  const loadCompletePreview = useCallback(async () => {
    if (!file) {
      setPreviewState(prev => ({
        ...prev,
        error: '请先选择要预览的文件',
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
      console.log('开始加载完整文档预览:', {
        fileName: file.name,
        chunkSize,
        chunkOverlap,
        splitByParagraph,
        splitBySentence
      });

      const preview = await getCompleteDocumentPreview(
        file,
        chunkSize,
        chunkOverlap,
        splitByParagraph,
        splitBySentence
      );

      console.log('获取到完整文档预览数据:', {
        success: preview.success,
        totalSegments: preview.total_segments,
        segmentsCount: preview.segments?.length || 0,
        parentContentLength: preview.parentContent?.length || 0,
        childrenCount: preview.childrenContent?.length || 0
      });

      setPreviewState({
        data: preview,
        isLoading: false,
        error: null,
        debugInfo: (preview as any).debugInfo || null
      });

      // 初始化展开状态 - 默认展开所有父块
      if (preview.segments) {
        const parentIds = new Set(preview.segments.map(segment => segment.id));
        setExpandedParents(parentIds);
      }

      // 通知父组件预览数据已准备好
      if (onPreviewDataReady && preview.doc_id && preview.segments) {
        onPreviewDataReady(preview.doc_id, preview.segments);
      }
    } catch (error: any) {
      console.error('加载完整文档预览失败:', error);

      // 根据错误类型提供更具体的错误信息
      let errorMessage = error.message || '未知错误';
      if (errorMessage.includes('文件不能为空')) {
        errorMessage = '请选择要预览的文件';
      } else if (errorMessage.includes('网络')) {
        errorMessage = '网络连接失败，请检查网络连接后重试';
      } else if (errorMessage.includes('不支持的文件类型')) {
        errorMessage = '不支持的文件类型，请选择 TXT、PDF 或 MD 文件';
      } else if (errorMessage.includes('文件太大')) {
        errorMessage = '文件过大，请选择较小的文件';
      } else if (errorMessage.includes('401') || errorMessage.includes('未授权')) {
        errorMessage = '登录已过期，请重新登录';
      }

      setPreviewState(prev => ({
        ...prev,
        isLoading: false,
        error: `加载失败: ${errorMessage}`,
        debugInfo: {
          requestParams: {
            fileName: file?.name,
            chunkSize,
            chunkOverlap,
            splitByParagraph,
            splitBySentence
          },
          rawResponse: null,
          responseHeaders: null,
          error: {
            message: error.message,
            response: error.response?.data,
            status: error.response?.status
          }
        }
      }));
    }
  }, [file, chunkSize, chunkOverlap, splitByParagraph, splitBySentence]);

  const handleSegmentClick = useCallback((segmentId: number) => {
    setSelectedSegment(segmentId);
    if (onSegmentClick) {
      onSegmentClick(segmentId);
    }
  }, [onSegmentClick]);

  const toggleParentExpansion = useCallback((parentId: number) => {
    setExpandedParents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(parentId)) {
        newSet.delete(parentId);
      } else {
        newSet.add(parentId);
      }
      return newSet;
    });
  }, []);

  // 渲染子段落
  const renderChildSegments = useCallback((children: ChildSegment[], parentId: number) => {
    if (!children || children.length === 0) return null;

    return (
      <div className="ml-6 mt-2 space-y-1 border-l-2 border-gray-200 pl-4">
        {children.map((child, index) => (
          <div
            key={`${parentId}-${index}`}
            className={`p-2 border rounded cursor-pointer transition-colors text-sm
              ${selectedSegment === child.id
                ? 'border-blue-400 bg-blue-25'
                : 'hover:bg-gray-25 border-gray-150'
              }`}
            onClick={() => handleSegmentClick(child.id)}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-600">
                子块 {index + 1}
              </span>
              <span className="text-xs text-gray-400">
                {child.length} 字符
              </span>
            </div>
            <p className="text-xs text-gray-600 line-clamp-2">
              {child.content}
            </p>
          </div>
        ))}
      </div>
    );
  }, [selectedSegment, handleSegmentClick]);

  // 组件挂载时自动加载预览
  React.useEffect(() => {
    if (file) {
      loadCompletePreview();
    }
  }, [loadCompletePreview, file]);

  return (
    <div className="mt-6">
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-900">
              完整文档切割预览
              {previewState.data && ` (共 ${previewState.data.total_segments} 个段落)`}
            </h2>
            <div className="flex items-center space-x-2">
              {/* 调试信息按钮 */}
              {previewState.debugInfo && (
                <button
                  onClick={() => setShowDebugInfo(!showDebugInfo)}
                  className={`px-3 py-1 text-xs rounded-md transition-colors ${
                    showDebugInfo
                      ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  title="显示/隐藏调试信息"
                >
                  🔍 调试信息
                </button>
              )}
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
          </div>
          
          {/* 切割参数显示 */}
          <div className="bg-gray-50 rounded-lg p-3 grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">块大小：</span>
              <span className="font-medium">{chunkSize}</span>
              <span className="text-gray-400 ml-1">字符</span>
            </div>
            <div>
              <span className="text-gray-500">重叠大小：</span>
              <span className="font-medium">{chunkOverlap}</span>
              <span className="text-gray-400 ml-1">字符</span>
            </div>
            <div>
              <span className="text-gray-500">按段落分割：</span>
              <span className="font-medium">{splitByParagraph ? '是' : '否'}</span>
            </div>
            <div>
              <span className="text-gray-500">按句子分割：</span>
              <span className="font-medium">{splitBySentence ? '是' : '否'}</span>
            </div>
            {previewState.data && (
              <>
                <div>
                  <span className="text-gray-500">原始内容长度：</span>
                  <span className="font-medium">{previewState.data.parentContent?.length || 0}</span>
                  <span className="text-gray-400 ml-1">字符</span>
                </div>
                <div>
                  <span className="text-gray-500">子内容数量：</span>
                  <span className="font-medium">{previewState.data.childrenContent?.length || 0}</span>
                  <span className="text-gray-400 ml-1">个</span>
                </div>
              </>
            )}
          </div>

          {/* 调试信息显示 */}
          {showDebugInfo && previewState.debugInfo && (
            <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-yellow-800 mb-3">🔍 调试信息</h3>
              <div className="space-y-4">
                {/* 请求参数 */}
                <div>
                  <h4 className="text-xs font-medium text-yellow-700 mb-2">请求参数:</h4>
                  <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
                    {JSON.stringify(previewState.debugInfo.requestParams, null, 2)}
                  </pre>
                </div>

                {/* 响应数据 */}
                {previewState.debugInfo.rawResponse && (
                  <div>
                    <h4 className="text-xs font-medium text-yellow-700 mb-2">响应数据:</h4>
                    <pre className="text-xs bg-white p-2 rounded border overflow-x-auto max-h-60 overflow-y-auto">
                      {JSON.stringify(previewState.debugInfo.rawResponse, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 响应头 */}
                {previewState.debugInfo.responseHeaders && (
                  <div>
                    <h4 className="text-xs font-medium text-yellow-700 mb-2">响应头:</h4>
                    <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
                      {JSON.stringify(previewState.debugInfo.responseHeaders, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 错误信息 */}
                {previewState.debugInfo.error && (
                  <div>
                    <h4 className="text-xs font-medium text-red-700 mb-2">错误信息:</h4>
                    <pre className="text-xs bg-red-50 p-2 rounded border overflow-x-auto">
                      {JSON.stringify(previewState.debugInfo.error, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="p-4">
          {previewState.isLoading ? (
            <div className="flex flex-col items-center justify-center h-[400px]">
              <div className="animate-spin rounded-full h-10 w-10 border-3 border-blue-500 border-t-transparent mb-4" />
              <p className="text-sm text-gray-500">正在生成完整文档预览...</p>
            </div>
          ) : previewState.error ? (
            <div className="flex flex-col items-center justify-center h-[400px]">
              <div className="text-red-500 mb-4 text-center max-w-md">
                <svg className="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="text-base mb-2">{previewState.error}</div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={loadCompletePreview}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  重新加载
                </button>
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                >
                  关闭预览
                </button>
              </div>
            </div>
          ) : !previewState.data ? (
            <div className="flex items-center justify-center h-[400px] text-gray-500">
              <div className="text-center">
                <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>请选择文件开始预览</p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 统计信息 */}
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <h3 className="text-sm font-medium text-blue-900 mb-3">预览统计</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.parent_segments || 0}</div>
                    <div className="text-blue-700">父块数量</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.child_segments || 0}</div>
                    <div className="text-blue-700">子块数量</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.total_segments}</div>
                    <div className="text-blue-700">总段落数</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.parentContent?.length || 0}</div>
                    <div className="text-blue-700">原始字符数</div>
                  </div>
                </div>
              </div>

              {/* 层级段落列表 */}
              <div className="bg-gray-50 rounded-lg p-4 border">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-900">文档层级结构</h3>
                  <div className="text-xs text-gray-500">
                    {previewState.data.parent_segments} 个父块，{previewState.data.child_segments} 个子块
                  </div>
                </div>
                <div className="max-h-[500px] overflow-y-auto">
                  <div className="space-y-3">
                    {previewState.data.segments?.map((parentSegment) => {
                      const isExpanded = expandedParents.has(parentSegment.id);
                      const hasChildren = parentSegment.children && parentSegment.children.length > 0;

                      return (
                        <div key={parentSegment.id} className="bg-white rounded-lg border border-gray-200">
                          {/* 父段落 */}
                          <div
                            className={`p-3 cursor-pointer transition-colors rounded-lg
                              ${selectedSegment === parentSegment.id
                                ? 'border-blue-500 bg-blue-50'
                                : 'hover:bg-gray-50'
                              }`}
                            onClick={() => handleSegmentClick(parentSegment.id)}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-700">
                                  父块 {parentSegment.id + 1}
                                </span>
                                {hasChildren && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleParentExpansion(parentSegment.id);
                                    }}
                                    className="text-gray-400 hover:text-gray-600 transition-colors"
                                  >
                                    <svg
                                      className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                                      fill="none"
                                      viewBox="0 0 24 24"
                                      stroke="currentColor"
                                    >
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                  </button>
                                )}
                              </div>
                              <div className="flex items-center space-x-2 text-xs text-gray-400">
                                {hasChildren && (
                                  <span>{parentSegment.children.length} 个子块</span>
                                )}
                                <span>{parentSegment.length} 字符</span>
                                <span>位置: {parentSegment.start}-{parentSegment.end}</span>
                              </div>
                            </div>
                            <p className="text-sm text-gray-700 line-clamp-2">
                              {parentSegment.content}
                            </p>
                          </div>

                          {/* 子段落 */}
                          {hasChildren && isExpanded && renderChildSegments(parentSegment.children, parentSegment.id)}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* 原始内容预览 */}
              {previewState.data.parentContent && (
                <div className="bg-gray-50 rounded-lg p-4 border">
                  <h3 className="text-sm font-medium text-gray-900 mb-3">原始文档内容预览</h3>
                  <div className="bg-white rounded p-3 border max-h-[300px] overflow-y-auto">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {previewState.data.parentContent.length > 1000 
                        ? `${previewState.data.parentContent.substring(0, 1000)}...` 
                        : previewState.data.parentContent}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CompleteDocumentPreview;
