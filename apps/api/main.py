"""
FastAPI 应用工厂 —— 创建并配置 FastAPI 实例。

所有 API 路由通过 include_router 注册。
在 asgi.py 中，此 app 被挂载到 /api 路径下。
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from apps.api.routers import qa, knowledge

# ---------- FastAPI 应用实例 ----------
app = FastAPI(
    title="RAG 智能客服 API",
    description="基于 LangChain + Chroma 的 RAG 检索增强生成问答系统",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI:  /api/docs
    redoc_url="/redoc",        # ReDoc:       /api/redoc
    openapi_url="/openapi.json",
)

# ---------- CORS 中间件 ----------
# 注：allow_origins=["*"] 与 allow_credentials=True 组合会被浏览器拒绝
# （通配符源不允许携带凭证），故不开启 credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 注册路由 ----------
app.include_router(qa.router, prefix="/qa", tags=["🤖 智能问答"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["📚 知识库管理"])


# ---------- 健康检查 ----------
@app.get("/health", tags=["⚙️ 系统"])
def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "RAG 智能客服 API"}


# ---------- 静态页面 ----------
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'static')


@app.get("/", tags=["🖥️ 前端"], include_in_schema=False)
def landing_page():
    """知识引擎入口页面"""
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@app.get("/chat", tags=["🖥️ 前端"], include_in_schema=False)
def chat_page():
    """智能对话界面"""
    return FileResponse(os.path.join(STATIC_DIR, 'chat.html'))


@app.get("/upload", tags=["🖥️ 前端"], include_in_schema=False)
def upload_page():
    """知识库管理界面"""
    return FileResponse(os.path.join(STATIC_DIR, 'upload.html'))


@app.get("/info", tags=["⚙️ 系统"])
def api_info():
    """API 信息"""
    return {
        "service": "RAG 智能客服 API",
        "version": "1.0.0",
        "landing": "/api/",
        "chat_ui": "/api/chat",
        "upload_ui": "/api/upload",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "health": "/api/health",
    }
