"""
知识库 API 路由 —— 处理文档上传和知识库管理。

接口：
    POST /knowledge/upload        - 上传文本文件到知识库
    POST /knowledge/upload-text   - 上传纯文本内容到知识库
    GET  /knowledge/stats         - 获取知识库统计信息
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from apps.api.schemas import KnowledgeUploadResponse, KnowledgeStats
from apps.core.services import knowledge_base_service

router = APIRouter()

# 允许的文件类型
ALLOWED_EXTENSIONS = {"txt", "md", "csv", "json", "xml", "html", "log"}


@router.post("/upload", response_model=KnowledgeUploadResponse, summary="上传文件到知识库")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文本文件到知识库。

    支持 .txt / .md / .csv / .json 等文本文件格式。
    文件内容会被分块、向量化并存入 Chroma 向量数据库。
    """
    # 检查文件扩展名
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: .{ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")

        result = knowledge_base_service.upload_by_file_content(
            content, file.filename or "unknown.txt"
        )

        success = "[成功]" in result
        return KnowledgeUploadResponse(
            filename=file.filename or "unknown.txt",
            result=result,
            success=success,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/upload-text", response_model=KnowledgeUploadResponse, summary="上传文本内容到知识库")
async def upload_text(
    text: str = Form(..., description="文本内容"),
    filename: str = Form(default="manual_input.txt", description="来源文件名")
):
    """
    直接上传文本字符串到知识库（无需文件）。

    适用于 API 集成或程序化添加知识。
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    try:
        result = knowledge_base_service.upload_by_str(text, filename)
        success = "[成功]" in result or "[跳过]" in result
        return KnowledgeUploadResponse(
            filename=filename,
            result=result,
            success=success,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/stats", response_model=KnowledgeStats, summary="知识库统计")
async def get_stats():
    """获取知识库基本信息"""
    import config_data as config
    return KnowledgeStats(collection_name=config.collection_name)
