"""
Django Admin 配置 —— 在后台管理知识库文档、聊天会话和消息。
"""
from django.contrib import admin
from .models import KnowledgeDocument, ChatSession, ChatMessage


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'md5_hash', 'content_length', 'chunk_count', 'operator', 'created_at']
    list_filter = ['operator', 'created_at']
    search_fields = ['filename', 'md5_hash']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['role', 'content', 'created_at']
    can_delete = False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id']
    readonly_fields = ['session_id', 'created_at', 'updated_at']
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content']

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = "内容预览"
