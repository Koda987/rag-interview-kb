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


class SessionSummary(BaseModel):
    """会话摘要项"""
    session_id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题（取首条用户提问，截断显示）")
    message_count: int = Field(..., description="消息条数")
    updated_at: str = Field(..., description="最后活跃时间")


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: list[SessionSummary]


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


# ===================== 分段预览（Dify 式向导） =====================

class PreviewRequest(BaseModel):
    """分段预览请求：纯 CPU 切块，不调用任何外部 API"""
    text: str = Field(..., min_length=1, max_length=200_000, description="待分段文本")
    chunk_size: int = Field(default=300, ge=50, le=2000, description="分段最大长度（字符）")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="分段重叠（字符）")
    mode: str = Field(default="paragraph", description="分段标识符模式：paragraph / line / sentence")
    clean: bool = Field(default=True, description="是否清洗（合并连续空行与空白）")


class PreviewChunk(BaseModel):
    """预览中的单个分段"""
    idx: int = Field(..., description="分段编号（从 1 开始）")
    length: int = Field(..., description="该段字符数")
    text: str = Field(..., description="分段内容（截断展示）")


class PreviewResponse(BaseModel):
    """分段预览响应"""
    total: int = Field(..., description="总分段数")
    total_chars: int = Field(..., description="原文总字符数")
    preview: list[PreviewChunk] = Field(default_factory=list, description="前若干段预览")
    truncated: bool = Field(..., description="是否只展示了部分分段")
