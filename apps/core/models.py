"""
Django Models —— RAG 项目的数据库模型。

存储知识库文件记录和对话记录，方便在 Django Admin 中管理。
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


class ChatSession(models.Model):
    """聊天会话记录"""
    session_id = models.CharField(max_length=128, unique=True, verbose_name="会话ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")

    class Meta:
        verbose_name = "聊天会话"
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return f"会话 {self.session_id}"


class ChatMessage(models.Model):
    """聊天消息记录"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', 'AI助手'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="所属会话"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="角色")
    content = models.TextField(verbose_name="消息内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "聊天消息"
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
