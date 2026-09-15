"""
服务层 —— 对外暴露统一的服务接口。

线程安全的单例服务，供 FastAPI 路由和 Django 管理命令调用。
"""
from .rag_service import rag_service
from .knowledge_base_service import knowledge_base_service
from .vector_store_service import vector_store_service
from .question_bank import question_bank
from .interviewer_service import interviewer_service

__all__ = [
    "rag_service",
    "knowledge_base_service",
    "vector_store_service",
    "question_bank",
    "interviewer_service",
]
