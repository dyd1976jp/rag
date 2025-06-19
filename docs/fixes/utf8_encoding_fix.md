# UTF-8编码错误修复报告

## 问题描述

### 原始错误
当使用curl命令向 `/api/v1/rag/documents/preview-split` 端点发送包含中文文件名的PDF文件（multipart/form-data格式）时，服务器返回500内部错误：

```
'utf-8' codec can't decode byte 0x93 in position 176: invalid start byte
```

### 错误发生场景
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/preview-split" \
  -F "file=@初赛训练数据集.pdf" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=512" \
  -F "child_chunk_overlap=50" \
  -F "child_separator=\n"
```

## 根本原因分析

1. **API端点设计问题**：`/documents/preview-split` 端点设计为接收JSON格式的纯文本内容，但客户端发送的是multipart/form-data格式的文件上传请求

2. **编码处理问题**：FastAPI在处理RequestValidationError时，遇到包含中文字符的PDF文件二进制数据，导致UTF-8解码失败

3. **异常处理缺陷**：默认的异常处理器无法安全处理包含二进制数据的验证错误

## 修复方案

### 1. 添加专门的RequestValidationError异常处理器

**文件**: `backend/app/main.py`

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    请求验证异常处理器
    
    专门处理RequestValidationError，避免在处理包含二进制数据的multipart/form-data请求时出现UTF-8编码错误。
    """
    try:
        # 安全地提取错误信息，避免编码问题
        error_details = []
        for error in exc.errors():
            safe_error = {
                "type": error.get("type", "validation_error"),
                "loc": [str(loc) for loc in error.get("loc", [])],
                "msg": str(error.get("msg", "Validation error"))
            }
            error_details.append(safe_error)
        
        # 检查是否是文件上传相关的错误
        url_path = str(request.url.path)
        if "upload" in url_path or "preview-split" in url_path:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "文件上传请求格式错误。请确保使用正确的端点：使用 /documents/upload 端点上传文件，并设置 preview_only=true 进行预览。",
                    "error_type": "file_upload_validation_error",
                    "suggestion": "对于文档预览分割，请使用 POST /api/v1/rag/documents/upload 端点，并在表单数据中设置 preview_only=true"
                }
            )
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": "请求参数验证失败",
                "errors": error_details
            }
        )
    except Exception as e:
        # 如果在处理验证错误时出现异常，返回简单的错误信息
        return JSONResponse(
            status_code=400,
            content={"detail": "请求格式错误，请检查请求参数"}
        )
```

### 2. 改进preview-split端点

**文件**: `backend/app/api/v1/endpoints/rag.py`

- 明确端点用途：仅用于纯文本内容预览
- 添加详细的API文档说明
- 改进参数验证和错误处理
- 使用Pydantic Field进行严格的参数验证

```python
class DocumentSplitRequest(BaseModel):
    content: str = Field(..., description="要分割的文本内容", min_length=1)
    parent_chunk_size: int = Field(1024, description="父块分段最大长度", gt=0)
    parent_chunk_overlap: int = Field(200, description="父块重叠长度", ge=0)
    parent_separator: str = Field("\n\n", description="父块分段标识符")
    child_chunk_size: int = Field(512, description="子块分段最大长度", gt=0)
    child_chunk_overlap: int = Field(50, description="子块重叠长度", ge=0)
    child_separator: str = Field("\n", description="子块分段标识符")
```

### 3. 增强文件上传处理

**文件**: `backend/app/api/v1/utils/document_utils.py`

改进 `save_uploaded_file` 函数，更好地处理中文文件名：

```python
def save_uploaded_file(file, upload_dir: str = "data/uploads") -> str:
    """
    保存上传的文件到临时位置，支持中文文件名
    """
    try:
        os.makedirs(upload_dir, exist_ok=True)
        
        # 安全处理文件名，避免编码问题
        filename = file.filename
        if not filename:
            filename = f"upload_{uuid.uuid4().hex[:8]}.tmp"
        
        # 确保文件名是有效的UTF-8字符串
        try:
            filename.encode('utf-8')
        except UnicodeEncodeError:
            # 如果文件名包含无法编码的字符，生成一个安全的文件名
            file_ext = os.path.splitext(filename)[1] if '.' in filename else ''
            filename = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
            logger.warning(f"文件名包含无法编码的字符，已重命名为: {filename}")
        
        # 处理文件名冲突
        file_path = os.path.join(upload_dir, filename)
        if os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
        
    except Exception as e:
        logger.error(f"保存上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
```

## 修复效果验证

### 测试结果

✅ **原始错误场景修复**：
- 修复前：`'utf-8' codec can't decode byte 0x93 in position 176: invalid start byte`
- 修复后：友好的400错误提示，指导用户使用正确的API端点

✅ **错误提示改进**：
```json
{
  "detail": "文件上传请求格式错误。请确保使用正确的端点：使用 /documents/upload 端点上传文件，并设置 preview_only=true 进行预览。",
  "error_type": "file_upload_validation_error",
  "suggestion": "对于文档预览分割，请使用 POST /api/v1/rag/documents/upload 端点，并在表单数据中设置 preview_only=true"
}
```

✅ **API功能正常**：
- 纯文本预览：`POST /api/v1/rag/documents/preview-split` (JSON格式)
- 文件上传预览：`POST /api/v1/rag/documents/upload` (multipart格式，preview_only=true)

### 验证命令

```bash
# 测试原始错误场景（现在返回友好错误）
curl -X POST "http://localhost:8000/api/v1/rag/documents/preview-split" \
  -F "file=@初赛训练数据集.pdf" \
  -F "parent_chunk_size=1024"

# 正确的文件上传预览
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -F "file=@初赛训练数据集.txt" \
  -F "preview_only=true" \
  -F "parent_chunk_size=1024"

# 正确的纯文本预览
curl -X POST "http://localhost:8000/api/v1/rag/documents/preview-split" \
  -H "Content-Type: application/json" \
  -d '{"content": "测试文本内容", "parent_chunk_size": 100}'
```

## API使用指导

### 文件上传预览
- **端点**: `POST /api/v1/rag/documents/upload`
- **格式**: multipart/form-data
- **参数**: 设置 `preview_only=true`
- **用途**: 上传文件并预览分割结果

### 纯文本预览
- **端点**: `POST /api/v1/rag/documents/preview-split`
- **格式**: JSON
- **用途**: 对已有文本内容进行分割预览

## 总结

本次修复成功解决了UTF-8编码错误问题，主要成果：

1. **✅ 消除UTF-8编码错误**：不再出现 `'utf-8' codec can't decode byte` 错误
2. **✅ 提供友好错误提示**：清晰指导用户使用正确的API端点
3. **✅ 改进文件名处理**：正确处理包含中文字符的文件名
4. **✅ 明确API职责**：区分文件上传和纯文本预览的使用场景
5. **✅ 增强系统稳定性**：避免因编码问题导致的服务崩溃

修复后的系统能够优雅地处理各种编码场景，为用户提供更好的API使用体验。
