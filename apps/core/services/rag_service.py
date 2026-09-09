"""
RAG 问答服务 —— 封装 LangChain RAG 链。

基于 rag.py，提供单例模式。
支持流式输出（stream）和非流式输出（invoke）。
"""
import logging
import threading
from typing import Generator, Optional
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from file_history_store import get_history
from .vector_store_service import vector_store_service
import config_data as config

logger = logging.getLogger(__name__)


class RagService:
    """RAG 问答服务（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "以我提供的已知参考资料为主，简洁和专业的回答用户问题。参考资料:{context}。"),
            ("system", "并且我提供用户的对话历史记录，如下："),
            MessagesPlaceholder("history"),
            ("user", "请回答用户提问：{input}")
        ])

        self.chat_model = ChatOpenAI(
            base_url=config.address,
            model=config.chat_model_name,
            temperature=0.7,
        )

        self.chain = self._build_chain()

    def _build_chain(self):
        """构建 RAG 执行链"""
        retriever = vector_store_service.get_retriever()

        def format_document(docs: list[Document]) -> str:
            if not docs:
                return "无相关参考资料"
            formatted_str = ""
            for doc in docs:
                # 只携带 source 供模型引用来源；完整 metadata（时间/操作者）
                # 对回答无益且浪费 token
                formatted_str += f"文档片段：{doc.page_content}\n来源：{doc.metadata.get('source', '未知')}\n\n"
            return formatted_str

        def format_for_retriever(value: dict) -> str:
            return value["input"]

        def format_for_prompt_template(value: dict) -> dict:
            return {
                "input": value["input"]["input"],
                "context": value["context"],
                "history": value["input"]["history"],
            }

        chain = (
            {
                "input": RunnablePassthrough(),
                "context": RunnableLambda(format_for_retriever) | retriever | format_document
            }
            | RunnableLambda(format_for_prompt_template)
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        return conversation_chain

    def invoke(self, prompt: str, session_id: str = "default") -> str:
        """
        非流式问答。

        Args:
            prompt: 用户输入
            session_id: 会话 ID（不同会话独立管理历史）

        Returns:
            AI 回复文本
        """
        session_config = {"configurable": {"session_id": session_id}}
        return self.chain.invoke({"input": prompt}, session_config)

    def stream(self, prompt: str, session_id: str = "default") -> Generator[str, None, None]:
        """
        流式问答 —— 逐 token 返回。

        Args:
            prompt: 用户输入
            session_id: 会话 ID

        Yields:
            token 字符串片段
        """
        session_config = {"configurable": {"session_id": session_id}}
        for chunk in self.chain.stream({"input": prompt}, session_config):
            yield chunk

    def get_history(self, session_id: str = "default") -> list[dict]:
        """
        获取指定会话的对话历史。

        Args:
            session_id: 会话 ID

        Returns:
            消息历史列表 [{"role": "user"/"assistant", "content": "..."}, ...]
        """
        try:
            history_obj = get_history(session_id)
            messages: list[BaseMessage] = history_obj.messages
            result = []
            for msg in messages:
                role = "user" if msg.type == "human" else "assistant"
                result.append({"role": role, "content": msg.content})
            return result
        except Exception as e:
            logger.warning("读取会话 %s 的历史失败: %s", session_id, e)
            return []

    def clear_history(self, session_id: str = "default") -> bool:
        """清除指定会话的历史记录"""
        try:
            history_obj = get_history(session_id)
            history_obj.clear()
            return True
        except Exception as e:
            logger.warning("清除会话 %s 的历史失败: %s", session_id, e)
            return False


# 全局单例
rag_service = RagService()
