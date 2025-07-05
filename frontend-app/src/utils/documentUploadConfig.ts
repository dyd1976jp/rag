/**
 * 文档上传配置统一管理模块
 * 用于消除代码重复，提供统一的文档上传参数配置
 */

// ==================== 类型定义 ====================

/**
 * 文档切割参数接口
 */
export interface DocumentSplitterParams {
  parent_chunk_size: number;
  parent_chunk_overlap: number;
  parent_separator: string;
  child_chunk_size: number;
  child_chunk_overlap: number;
  child_separator: string;
}

/**
 * 上传模式配置接口
 */
export interface UploadModeConfig {
  preview_only: boolean;
  use_new_processor?: boolean;
  processor_type?: string;    // 添加
  parent_mode?: string;       // 添加
}

/**
 * 完整的文档上传配置接口
 */
export interface DocumentUploadConfig extends DocumentSplitterParams, UploadModeConfig {}

/**
 * 调试用的请求参数接口
 */
export interface RequestParams extends DocumentUploadConfig {
  file: {
    name: string;
    size: number;
    type: string;
  };
}

// ==================== 配置常量 ====================

/**
 * 默认的文档切割参数
 * 注意：这些参数与原始代码保持一致
 * - parent_chunk_size: 512
 * - parent_chunk_overlap: 50
 * - child_chunk_size: 256 (parent_chunk_size / 2)
 * - child_chunk_overlap: 12 (parent_chunk_overlap / 4)
 */
export const DEFAULT_SPLITTER_PARAMS: DocumentSplitterParams = {
  parent_chunk_size: 512,
  parent_chunk_overlap: 50,
  parent_separator: String.fromCharCode(92, 110, 92, 110),  // 修复：构造 \n\n 字符串（与curl一致）
  child_chunk_size: 256,
  child_chunk_overlap: 12,  // 修正：原始代码使用 50 / 4 = 12
  child_separator: String.fromCharCode(92, 110)             // 修复：构造 \n 字符串（与curl一致）
};

/**
 * 预定义的上传模式配置
 */
export const UPLOAD_MODES = {
  /** 预览模式：只进行文档切割预览，不保存到数据库 */
  PREVIEW: {
    preview_only: true,
    use_new_processor: false,
    processor_type: "parent_child",  // 添加
    parent_mode: "paragraph"         // 添加
  } as UploadModeConfig,
  
  /** 上传模式：完整处理并保存文档 */
  UPLOAD: {
    preview_only: false
  } as UploadModeConfig
};

// ==================== 工具函数 ====================

/**
 * 根据父块参数计算子块参数
 * 计算逻辑与原始代码保持一致：
 * - child_chunk_size = Math.floor(parent_chunk_size / 2)
 * - child_chunk_overlap = Math.floor(parent_chunk_overlap / 4)
 * @param parentChunkSize 父块大小
 * @param parentChunkOverlap 父块重叠大小
 * @returns 计算后的子块参数
 */
export function calculateChildParams(parentChunkSize: number, parentChunkOverlap: number) {
  return {
    child_chunk_size: Math.floor(parentChunkSize / 2),
    child_chunk_overlap: Math.floor(parentChunkOverlap / 4)  // 确保与原始代码一致
  };
}

/**
 * 创建完整的文档上传配置
 * @param customParams 自定义参数（可选）
 * @param mode 上传模式
 * @returns 完整的上传配置
 */
export function createUploadConfig(
  customParams: Partial<DocumentSplitterParams> = {},
  mode: UploadModeConfig = UPLOAD_MODES.UPLOAD
): DocumentUploadConfig {
  const baseParams = { ...DEFAULT_SPLITTER_PARAMS, ...customParams };
  
  // 如果提供了父块参数但没有提供子块参数，则自动计算
  if (customParams.parent_chunk_size && !customParams.child_chunk_size) {
    const childParams = calculateChildParams(
      customParams.parent_chunk_size,
      customParams.parent_chunk_overlap || DEFAULT_SPLITTER_PARAMS.parent_chunk_overlap
    );
    Object.assign(baseParams, childParams);
  }
  
  return {
    ...baseParams,
    ...mode
  };
}

/**
 * 创建用于上传的 FormData 对象
 * @param file 要上传的文件
 * @param config 上传配置
 * @returns 配置好的 FormData 对象
 */
export function createUploadFormData(file: File, config: DocumentUploadConfig): FormData {
  const formData = new FormData();
  
  // 添加文件
  formData.append('file', file);
  
  // 添加切割参数
  formData.append('parent_chunk_size', config.parent_chunk_size.toString());
  formData.append('parent_chunk_overlap', config.parent_chunk_overlap.toString());
  formData.append('parent_separator', config.parent_separator);
  formData.append('child_chunk_size', config.child_chunk_size.toString());
  formData.append('child_chunk_overlap', config.child_chunk_overlap.toString());
  formData.append('child_separator', config.child_separator);
  
  // 添加模式参数
  formData.append('preview_only', config.preview_only.toString());
  if (config.use_new_processor !== undefined) {
    formData.append('use_new_processor', config.use_new_processor.toString());
  }
  if (config.processor_type !== undefined) {
    formData.append('processor_type', config.processor_type);
  }
  if (config.parent_mode !== undefined) {
    formData.append('parent_mode', config.parent_mode);
  }
  
  return formData;
}

/**
 * 创建用于调试的请求参数对象
 * @param file 上传的文件
 * @param config 上传配置
 * @returns 调试用的请求参数对象
 */
export function createRequestParams(file: File, config: DocumentUploadConfig): RequestParams {
  return {
    file: {
      name: file.name,
      size: file.size,
      type: file.type
    },
    ...config
  };
}

// ==================== 便捷函数 ====================

/**
 * 创建预览模式的 FormData
 * @param file 要预览的文件
 * @param chunkSize 自定义块大小（可选）
 * @param chunkOverlap 自定义重叠大小（可选）
 * @returns 配置好的 FormData 对象
 */
export function createPreviewFormData(
  file: File,
  chunkSize?: number,
  chunkOverlap?: number
): FormData {
  const customParams: Partial<DocumentSplitterParams> = {};
  if (chunkSize) customParams.parent_chunk_size = chunkSize;
  if (chunkOverlap) customParams.parent_chunk_overlap = chunkOverlap;
  
  const config = createUploadConfig(customParams, UPLOAD_MODES.PREVIEW);
  return createUploadFormData(file, config);
}

/**
 * 创建上传模式的 FormData
 * @param file 要上传的文件
 * @returns 配置好的 FormData 对象
 */
export function createUploadFormDataForUpload(file: File): FormData {
  const config = createUploadConfig({}, UPLOAD_MODES.UPLOAD);
  return createUploadFormData(file, config);
}
