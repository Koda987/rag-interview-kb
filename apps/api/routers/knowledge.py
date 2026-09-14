"""
知识库 API 路由 —— 处理文档上传和知识库管理。

接口：
    POST /knowledge/upload        - 上传文本文件到知识库
    POST /knowledge/upload-text   - 上传纯文本内容到知识库
    GET  /knowledge/stats         - 获取知识库统计信息
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from apps.api.schemas import KnowledgeUploadResponse, KnowledgeStats
from apps.core.services import knowledge_base_service
import config_data as config

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

        # 上传含阻塞的向量化 API 调用，放入线程池执行，
        # 避免卡住事件循环（否则上传期间聊天/流式输出都会被阻塞）
        result = await run_in_threadpool(
            knowledge_base_service.upload_by_file_content,
            content, file.filename or "unknown.txt"
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
        return KnowledgeUploadResponse(
            filename=filename,
            status=result["status"],
            chunks=result["chunks"],
            message=result["message"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


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
