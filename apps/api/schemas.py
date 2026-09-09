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
    filename: str = Field(..., description="文件名")
    status: str = Field(..., description="结果状态: success / skipped / error")
    chunks: int = Field(..., description="本次入库的分块数")
    message: str = Field(..., description="人类可读的结果描述")


class KnowledgeStats(BaseModel):
    """知识库统计信息"""
    collection_name: str = Field(..., description="向量库集合名")
    chunks: int = Field(..., description="向量块总数")
    documents: Optional[int] = Field(default=None, description="文档记录数（Django）")
    last_updated: Optional[str] = Field(default=None, description="最近入库时间")
