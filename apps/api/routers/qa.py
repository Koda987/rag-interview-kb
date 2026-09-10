"""
问答 API 路由 —— 处理 RAG 智能问答请求。

接口：
    POST  /qa/ask          - 非流式问答
    POST  /qa/stream       - 流式问答（SSE）
    GET   /qa/sessions     - 会话列表
    GET   /qa/history      - 获取对话历史
    DELETE /qa/history     - 清除对话历史
"""
import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from apps.api.schemas import (
    QARequest, QAResponse,
    ChatHistoryResponse, ChatHistoryItem,
    ClearHistoryRequest, ClearHistoryResponse,
    SessionListResponse,
)
from apps.core.services import rag_service

router = APIRouter()

# 与存储层 file_history_store.SESSION_ID_PATTERN 保持一致
SESSION_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def _validate_session_id(session_id: str) -> None:
    """会话 ID 最终会拼进文件路径，非法值可能造成路径穿越"""
    if not SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(
            status_code=400,
            detail="非法会话 ID：仅允许字母、数字、下划线、连字符，长度 1-64",
        )


@router.post("/ask", response_model=QAResponse, summary="非流式问答")
def ask(request: QARequest):
    """
    RAG 智能问答（非流式）。

    将用户问题通过 RAG 检索引擎检索相关文档，结合对话历史生成回答。
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    _validate_session_id(request.session_id)

    try:
        answer = rag_service.invoke(request.question, request.session_id)
        return QAResponse(
            answer=answer,
            session_id=request.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答服务异常: {str(e)}")


@router.post("/stream", summary="流式问答（SSE）")
def ask_stream(request: QARequest):
    """
    RAG 智能问答（流式 SSE）。

    以 Server-Sent Events 形式逐 token 返回 AI 回答，
    前端使用 fetch + ReadableStream 接收并逐块渲染。
    每个 chunk 用 JSON 包一层（{"text": "..."}），避免文本内含
    换行符时破坏 SSE 帧分隔；[DONE] 为结束哨兵。
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    _validate_session_id(request.session_id)  # 流式一旦开始就无法再返回 400，必须提前校验

    def generate():
        try:
            for chunk in rag_service.stream(request.question, request.session_id):
                # SSE 格式: data: <json>\n\n
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/sessions", response_model=SessionListResponse, summary="会话列表")
def list_sessions():
    """列出全部历史会话（标题、消息条数、最后活跃时间，按活跃倒序）"""
    return SessionListResponse(sessions=rag_service.get_sessions())


@router.get("/history", response_model=ChatHistoryResponse, summary="获取对话历史")
def get_history(session_id: str = "default"):
    """获取指定会话的对话历史记录"""
    _validate_session_id(session_id)
    messages_data = rag_service.get_history(session_id)
    messages = [
        ChatHistoryItem(role=m["role"], content=m["content"])
        for m in messages_data
    ]
    return ChatHistoryResponse(session_id=session_id, messages=messages)


@router.delete("/history", response_model=ClearHistoryResponse, summary="清除对话历史")
def clear_history(request: ClearHistoryRequest):
    """清除指定会话的对话历史"""
    _validate_session_id(request.session_id)
    success = rag_service.clear_history(request.session_id)
    return ClearHistoryResponse(
        success=success,
        message="历史记录已清除" if success else "清除失败，会话不存在"
    )
