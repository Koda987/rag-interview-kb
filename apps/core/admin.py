"""
Django Admin 配置 —— 在后台管理知识库文档上传记录。

对话历史按会话存 JSON 文件（file_history_store.py），不入库、无 Admin。
"""
from django.contrib import admin
from .models import KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'md5_hash', 'content_length', 'chunk_count', 'operator', 'created_at']
    list_filter = ['operator', 'created_at']
    search_fields = ['filename', 'md5_hash']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
