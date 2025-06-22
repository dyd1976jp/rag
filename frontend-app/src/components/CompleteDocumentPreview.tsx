import React, { useState, useCallback } from 'react';
import { getCompleteDocumentPreview, CompleteDocumentPreviewResponse } from '../api/documentCollections';

interface CompleteDocumentPreviewProps {
  file: File | null;
  chunkSize: number;
  chunkOverlap: number;
  splitByParagraph: boolean;
  splitBySentence: boolean;
  onClose: () => void;
  onSegmentClick?: (segmentId: number) => void;
}

interface PreviewState {
  data: CompleteDocumentPreviewResponse | null;
  isLoading: boolean;
  error: string | null;
}

const CompleteDocumentPreview: React.FC<CompleteDocumentPreviewProps> = ({
  file,
  chunkSize,
  chunkOverlap,
  splitByParagraph,
  splitBySentence,
  onClose,
  onSegmentClick
}) => {
  const [previewState, setPreviewState] = useState<PreviewState>({
    data: null,
    isLoading: false,
    error: null
  });

  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);

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
        error: null
      });
    } catch (error: any) {
      console.error('加载完整文档预览失败:', error);
      setPreviewState(prev => ({
        ...prev,
        isLoading: false,
        error: `加载失败: ${error.message || '未知错误'}`
      }));
    }
  }, [file, chunkSize, chunkOverlap, splitByParagraph, splitBySentence]);

  const handleSegmentClick = useCallback((segmentId: number) => {
    setSelectedSegment(segmentId);
    if (onSegmentClick) {
      onSegmentClick(segmentId);
    }
  }, [onSegmentClick]);

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
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.total_segments}</div>
                    <div className="text-blue-700">总段落数</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.parentContent?.length || 0}</div>
                    <div className="text-blue-700">原始字符数</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{previewState.data.childrenContent?.length || 0}</div>
                    <div className="text-blue-700">子内容数</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {previewState.data.segments ? Math.round(previewState.data.parentContent.length / previewState.data.segments.length) : 0}
                    </div>
                    <div className="text-blue-700">平均段落长度</div>
                  </div>
                </div>
              </div>

              {/* 段落列表 */}
              <div className="bg-gray-50 rounded-lg p-4 border">
                <h3 className="text-sm font-medium text-gray-900 mb-3">所有段落列表</h3>
                <div className="max-h-[500px] overflow-y-auto">
                  <div className="space-y-2">
                    {previewState.data.segments?.map((segment) => (
                      <div
                        key={segment.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors
                          ${selectedSegment === segment.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'hover:bg-gray-50 border-gray-200'
                          }`}
                        onClick={() => handleSegmentClick(segment.id)}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-500">
                            段落 {segment.id + 1}
                          </span>
                          <span className="text-xs text-gray-400">
                            {segment.length} 字符 (位置: {segment.start}-{segment.end})
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 line-clamp-2">
                          {segment.content}
                        </p>
                      </div>
                    ))}
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
