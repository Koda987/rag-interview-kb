"""
知识库 API 路由 —— 处理文档上传和知识库管理。

接口：
    POST /knowledge/upload        - 上传文本文件到知识库（可带分段参数）
    POST /knowledge/upload-text   - 上传纯文本内容到知识库（可带分段参数）
    POST /knowledge/preview       - 分段预览（Dify 式向导，纯切块不入库）
    GET  /knowledge/stats         - 获取知识库统计信息
    GET  /knowledge/contents      - 已录入文档 + 知识块预览
    DELETE /knowledge/document    - 删除已录入文档
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from apps.api.schemas import (
    KnowledgeUploadResponse, KnowledgeStats,
    PreviewRequest, PreviewResponse, PreviewChunk,
)
from apps.core.services import knowledge_base_service
from apps.core.services.chunking import SEPARATOR_MODES, make_preview
import config_data as config

router = APIRouter()

# 允许的文件类型
ALLOWED_EXTENSIONS = {"txt", "md", "csv", "json", "xml", "html", "log"}


@router.post("/upload", response_model=KnowledgeUploadResponse, summary="上传文件到知识库")
async def upload_file(
    file: UploadFile = File(...),
    chunk_size: Optional[int] = Form(default=None, ge=50, le=2000, description="分段最大长度"),
    chunk_overlap: Optional[int] = Form(default=None, ge=0, le=500, description="分段重叠"),
    mode: Optional[str] = Form(default=None, description="分段模式 paragraph/line/sentence"),
    clean: Optional[bool] = Form(default=None, description="是否清洗文本"),
):
    """
    上传文本文件到知识库。

    支持 .txt / .md / .csv / .json 等文本文件格式。
    文件内容会被分块、向量化并存入 Chroma 向量数据库。
    可选分段参数不传时使用服务端默认值（chunk 300 / overlap 50）。
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

        # 上传含阻塞的向量化 API 调用，放入线程池执行，
        # 避免卡住事件循环（否则上传期间聊天/流式输出都会被阻塞）
        result = await run_in_threadpool(
            knowledge_base_service.upload_by_file_content,
            content, file.filename or "unknown.txt",
            chunk_size, chunk_overlap, mode, clean,
        )
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return KnowledgeUploadResponse(
            filename=file.filename or "unknown.txt",
            status=result["status"],
            chunks=result["chunks"],
            message=result["message"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/upload-text", response_model=KnowledgeUploadResponse, summary="上传文本内容到知识库")
def upload_text(
    text: str = Form(..., description="文本内容"),
    filename: str = Form(default="manual_input.txt", description="来源文件名"),
    chunk_size: Optional[int] = Form(default=None, ge=50, le=2000, description="分段最大长度"),
    chunk_overlap: Optional[int] = Form(default=None, ge=0, le=500, description="分段重叠"),
    mode: Optional[str] = Form(default=None, description="分段模式 paragraph/line/sentence"),
    clean: Optional[bool] = Form(default=None, description="是否清洗文本"),
):
    """
    直接上传文本字符串到知识库（无需文件）。

    适用于 API 集成或程序化添加知识；可选分段参数同 /upload。
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    try:
        result = knowledge_base_service.upload_by_str(
            text, filename, chunk_size, chunk_overlap, mode, clean,
        )
        return KnowledgeUploadResponse(
            filename=filename,
            status=result["status"],
            chunks=result["chunks"],
            message=result["message"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/preview", response_model=PreviewResponse, summary="分段预览（Dify 式向导）")
def preview_chunks(request: PreviewRequest):
    """
    按给定分段参数切块并返回预览。

    纯 CPU 操作（不调用 embedding/大模型 API、不入库），
    供前端向导"文本分段与清洗"步骤实时预览。
    """
    if request.mode not in SEPARATOR_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的分段模式: {request.mode}，可选: {', '.join(SEPARATOR_MODES)}",
        )
    p = make_preview(
        request.text,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        mode=request.mode,
        clean=request.clean,
    )
    return PreviewResponse(
        total=p["total"],
        total_chars=p["total_chars"],
        preview=[PreviewChunk(**c) for c in p["preview"]],
        truncated=p["truncated"],
    )


@router.get("/stats", response_model=KnowledgeStats, summary="知识库统计")
def get_stats():
    """获取知识库统计：向量块数、文档记录数、最近入库时间

    注意保持同步 def：FastAPI 会放入线程池执行；
    async def 里直接调 Django ORM 会触发
    SynchronousOnlyOperation 异常。
    """
    s = knowledge_base_service.stats()
    return KnowledgeStats(
        collection_name=config.collection_name,
        documents=s["documents"],
        chunks=s["chunks"],
        last_updated=s["last_updated"],
    )


@router.get("/contents", summary="知识库内容：已录入文档 + 知识块预览")
def get_contents(limit: int = 12, source: str | None = None):
    """已录入文档列表 + 知识块内容预览。

    注意保持同步 def：内部读取 Django ORM 与 Chroma，
    FastAPI 会放入线程池执行。
    source 传入来源文件名时，只返回该文件的知识块。
    """
    return {
        "documents": knowledge_base_service.documents(),
        "chunks": knowledge_base_service.preview_chunks(limit=limit, source=source),
    }


@router.delete("/document", summary="删除已录入文档")
def remove_document(filename: str):
    """删除指定文档：同时清除其全部知识块（Chroma）、上传记录（Django）与 MD5 去重记录。

    注意保持同步 def：内部读取 Django ORM 与 Chroma，FastAPI 会放入线程池执行。
    """
    if not filename.strip():
        raise HTTPException(status_code=400, detail="filename 不能为空")
    result = knowledge_base_service.delete_document(filename.strip())
    return result
