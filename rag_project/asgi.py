"""
ASGI 配置 —— 整合 Django + FastAPI + 前端聊天页面。

路由分发（按优先级匹配）:
    /api/*          -> FastAPI（REST API + Swagger 文档 + 聊天页面）
    /               -> 前端聊天界面（static/index.html）
    /admin/* 等      -> Django Admin 管理后台
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_project.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import FileResponse

# 导入 FastAPI 应用
from apps.api.main import app as fastapi_app

# Django ASGI 应用
django_asgi_app = get_asgi_application()

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')


def serve_chat_page(request):
    """服务前端聊天界面"""
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


# Starlette 路由合并（按顺序匹配，先匹配先生效）
application = Starlette(routes=[
    Mount("/api", fastapi_app),       # /api/*    -> FastAPI
    Route("/", serve_chat_page),      # /         -> 聊天界面
    Mount("/", django_asgi_app),      # /*        -> Django (admin 等)
])
