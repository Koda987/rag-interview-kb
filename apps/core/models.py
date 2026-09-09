"""
Django Models —— RAG 项目的数据库模型。

知识库文件上传记录，方便在 Django Admin 中管理。
对话历史不走数据库（按会话存 JSON 文件，见 file_history_store.py）。
"""
from django.db import models


class KnowledgeDocument(models.Model):
    """知识库文档记录"""
    filename = models.CharField(max_length=255, verbose_name="文件名")
    md5_hash = models.CharField(max_length=64, unique=True, verbose_name="MD5哈希")
    content_length = models.IntegerField(default=0, verbose_name="内容长度")
    chunk_count = models.IntegerField(default=0, verbose_name="分块数量")
    operator = models.CharField(max_length=100, default="admin", verbose_name="操作者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "知识库文档"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
