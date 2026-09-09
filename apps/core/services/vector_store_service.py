"""
向量存储服务 —— 封装 Chroma 向量检索。

基于 vector_stores.py，提供单例模式供全局使用。
"""
import threading
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import config_data as config


class VectorStoreService:
    """向量存储服务（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, embedding=None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        self.embedding = embedding or OpenAIEmbeddings(
            openai_api_base=config.address,
            model=config.embedding_model_name,
        )

        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )

    def get_retriever(self):
        """返回向量检索器，方便加入 LangChain chain"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": config.similarity_threshold}
        )

    def get_store(self):
        """直接返回 Chroma 向量存储实例"""
        return self.vector_store

    def search(self, query: str, k: int = None) -> list:
        """直接搜索，返回文档列表"""
        k = k or config.similarity_threshold
        return self.vector_store.similarity_search(query, k=k)


# 全局单例
vector_store_service = VectorStoreService()
