"""
知识库服务 —— 封装文档上传、分块、向量化。

基于 knowledge_base.py，提供单例模式。
支持将上传记录同步到 Django 数据库。
"""
import os
import hashlib
import threading
from datetime import datetime
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config_data as config


def _get_string_md5(input_str: str, encoding: str = 'utf-8') -> str:
    """将传入的字符串转换为 md5 字符串"""
    str_bytes = input_str.encode(encoding=encoding)
    md5_obj = hashlib.md5()
    md5_obj.update(str_bytes)
    return md5_obj.hexdigest()


def _check_md5(md5_str: str) -> bool:
    """检查 md5 是否已处理过"""
    if not os.path.exists(config.md5_path):
        open(config.md5_path, 'w', encoding='utf-8').close()
        return False
    for line in open(config.md5_path, 'r', encoding='utf-8').readlines():
        if line.strip() == md5_str:
            return True
    return False


def _save_md5(md5_str: str) -> None:
    """将 md5 字符串记录到文件"""
    with open(config.md5_path, 'a', encoding='utf-8') as f:
        f.write(md5_str + '\n')


class KnowledgeBaseService:
    """知识库服务（单例）"""

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

        os.makedirs(config.persist_directory, exist_ok=True)

        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=OpenAIEmbeddings(
                openai_api_base=config.address,
                model=config.embedding_model_name,
            ),
            persist_directory=config.persist_directory,
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        )

    def upload_by_str(self, data: str, filename: str) -> str:
        """
        将传入字符串进行向量化并存入向量数据库。

        Args:
            data: 文本内容
            filename: 来源文件名

        Returns:
            状态描述字符串
        """
        md5_hex = _get_string_md5(data)

        if _check_md5(md5_hex):
            self._save_to_db(filename, md5_hex, len(data), 0)
            return f"[跳过] 内容已存在于知识库中 (MD5: {md5_hex[:8]}...)"

        # 文本分块
        if len(data) > config.max_split_char_number:
            knowledge_chunks: list[str] = self.spliter.split_text(data)
        else:
            knowledge_chunks = [data]

        metadata = {
            "source": filename,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "admin",
        }

        chunk_count = len(knowledge_chunks)
        self.chroma.add_texts(
            knowledge_chunks,
            metadatas=[metadata.copy() for _ in knowledge_chunks],
        )

        _save_md5(md5_hex)
        self._save_to_db(filename, md5_hex, len(data), chunk_count)

        return f"[成功] 内容已载入向量库，共 {chunk_count} 个分块"

    def upload_by_file_content(self, content: bytes, filename: str) -> str:
        """
        直接从文件字节内容上传（FastAPI 文件上传接口调用）。

        Args:
            content: 文件字节内容
            filename: 文件名

        Returns:
            状态描述字符串
        """
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('gbk')
            except UnicodeDecodeError:
                return "[失败] 文件编码不支持，请使用 UTF-8 编码的文本文件"
        return self.upload_by_str(text, filename)

    def _save_to_db(self, filename: str, md5_hash: str, content_length: int, chunk_count: int):
        """将上传记录同步到 Django 数据库（可选）"""
        try:
            from apps.core.models import KnowledgeDocument
            KnowledgeDocument.objects.update_or_create(
                md5_hash=md5_hash,
                defaults={
                    'filename': filename,
                    'content_length': content_length,
                    'chunk_count': chunk_count,
                    'operator': 'admin',
                }
            )
        except Exception:
            pass  # Django 未初始化时静默跳过


# 全局单例
knowledge_base_service = KnowledgeBaseService()
