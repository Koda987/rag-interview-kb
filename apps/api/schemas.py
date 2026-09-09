"""
Pydantic 数据模型 —— FastAPI 请求/响应的 Schema 定义。
"""
from pydantic import BaseModel, Field
from typing import Optional


# ===================== 问答相关 =====================

class QARequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")
    session_id: str = Field(default="default", description="会话ID，用于区分不同用户/会话")


class QAResponse(BaseModel):
    """问答响应（非流式）"""
    answer: str = Field(..., description="AI 回答")
    session_id: str = Field(..., description="会话ID")
    references: list[str] = Field(default=[], description="参考文档来源列表")


class ChatHistoryItem(BaseModel):
    """历史消息项"""
    role: str = Field(..., description="角色: user / assistant")
    content: str = Field(..., description="消息内容")


class ChatHistoryResponse(BaseModel):
    """对话历史响应"""
    session_id: str
    messages: list[ChatHistoryItem]


class ClearHistoryRequest(BaseModel):
    """清除历史请求"""
    session_id: str = Field(default="default", description="要清除的会话ID")


class ClearHistoryResponse(BaseModel):
    """清除历史响应"""
    success: bool
    message: str


# ===================== 知识库相关 =====================

class KnowledgeUploadResponse(BaseModel):
    """知识库上传响应"""
    filename: str
    result: str
    success: bool


class KnowledgeStats(BaseModel):
    """知识库统计信息"""
    collection_name: str


class ErrorResponse(BaseModel):
    """通用错误响应"""
    detail: str
    error_code: Optional[str] = None
