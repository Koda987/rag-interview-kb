#!/usr/bin/env python
"""
启动脚本 —— 运行 Django + FastAPI 服务。

使用方式:
    python run.py                     # 默认端口 8001，开发模式
    python run.py --port 8080         # 指定端口
    python run.py --host 0.0.0.0     # 允许外部访问
    python run.py --reload            # 开启热重载（开发环境）

首次运行前请执行:
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser   # 创建 Django Admin 管理员
"""
import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="启动 AI 面试八股知识引擎（Django + FastAPI）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="监听端口 (默认: 8001)")
    parser.add_argument("--reload", action="store_true", help="开启热重载（开发模式）")
    args = parser.parse_args()

    # 确保项目根目录在 Python 路径中
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)

    # 设置 Django 环境变量
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_project.settings')

    # 初始化 Django（在 uvicorn 之前）
    import django
    django.setup()

    import uvicorn

    print("=" * 60)
    print("  AI 面试八股知识引擎 启动中...")
    print(f"  聊天界面:            http://{args.host}:{args.port}")
    print(f"  API 文档 (Swagger):  http://{args.host}:{args.port}/api/docs")
    print(f"  API 文档 (ReDoc):    http://{args.host}:{args.port}/api/redoc")
    print(f"  Django Admin:        http://{args.host}:{args.port}/admin")
    print(f"  健康检查:            http://{args.host}:{args.port}/api/health")
    print("=" * 60)

    # 嵌入服务在模块导入期就要读密钥，提前拦截给出可操作的提示，
    # 避免甩出一屏 traceback
    if not os.environ.get("OPENAI_API_KEY"):
        print()
        print("  [启动失败] 当前终端缺少环境变量 OPENAI_API_KEY")
        print("  Windows 用户级环境变量只对「之后新开的」进程生效——")
        print("  如果这是 VS Code 内置终端，请完全退出 VS Code 重开，")
        print("  或改用开始菜单新开的 PowerShell 窗口运行。")
        print("  临时方案：在本终端执行下面命令后重试：")
        print('    $env:OPENAI_API_KEY = "你的密钥"')
        sys.exit(1)

    uvicorn.run(
        "rag_project.asgi:application",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == '__main__':
    main()
