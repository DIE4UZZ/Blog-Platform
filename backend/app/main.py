"""
main.py —— FastAPI 应用入口

职责：
  1. 创建 FastAPI 实例并完成全局配置（CORS、静态文件挂载）
  2. 注册所有业务路由（用户、文章、评论、行为、推荐、分析、社交、书库、排行、上传、管理）
  3. 注册启动事件（初始化数据库表）
  4. 注册全局异常处理器，将 HTTP 异常统一转换为业务标准响应格式
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings          # 读取应用配置
from backend.app.core.response import error_response      # 构造错误响应体
from backend.app.db.init_db import init_db                # 初始化数据库表
from backend.app.routers import (                         # 各业务路由模块
    admin,
    analysis,
    article,
    behavior,
    comment,
    interaction,
    library,
    rank,
    recommend,
    social,
    upload,
    user,
)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    步骤：
      1. 读取配置，创建 FastAPI 实例
      2. 确保上传目录存在
      3. 添加 CORS 中间件（允许跨域请求）
      4. 注册所有业务路由，统一前缀 /api
      5. 挂载静态文件目录 /uploads
      6. 注册启动事件：应用启动时自动建表
      7. 注册全局 HTTP 异常处理器，将 4xx/5xx 转为统一 JSON 格式

    Returns:
        FastAPI: 配置完成的应用实例。
    """

    settings = get_settings()
    app = FastAPI(title="Blog Platform API")

    # 确保图片上传目录存在，不存在则自动创建
    upload_dir = Path("backend/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # ── CORS 中间件 ──────────────────────────────────────────────────────────
    # 允许前端跨域访问后端 API，生产环境应将 allow_origins 限制为具体域名
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,   # 允许的来源列表，默认 ["*"]
        allow_credentials=True,                # 允许携带 Cookie / Authorization
        allow_methods=["*"],                   # 允许所有 HTTP 方法
        allow_headers=["*"],                   # 允许所有请求头
    )

    # ── 路由注册 ─────────────────────────────────────────────────────────────
    # 每个路由模块对应一个业务域，统一挂载到 /api 前缀下
    app.include_router(user.router, prefix="/api")          # 用户注册/登录/信息
    app.include_router(article.router, prefix="/api")       # 文章发布/编辑/列表
    app.include_router(interaction.router, prefix="/api")   # 点赞/收藏互动
    app.include_router(comment.router, prefix="/api")       # 评论
    app.include_router(behavior.router, prefix="/api")      # 行为上报
    app.include_router(recommend.router, prefix="/api")     # 推荐算法
    app.include_router(analysis.router, prefix="/api")      # 数据分析
    app.include_router(social.router, prefix="/api")        # 关注/通知/动态流
    app.include_router(library.router, prefix="/api")       # 收藏夹/历史/稍后读
    app.include_router(rank.router, prefix="/api")          # 排行榜/热搜
    app.include_router(upload.router, prefix="/api")        # 图片上传
    app.include_router(admin.router, prefix="/api")         # 管理后台

    # 挂载静态文件服务，使上传的图片可通过 /uploads/<filename> 访问
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    # ── 启动事件 ─────────────────────────────────────────────────────────────
    @app.on_event("startup")
    def startup_event() -> None:
        """应用启动时自动创建/迁移数据库表。"""
        init_db()

    # ── 全局异常处理 ─────────────────────────────────────────────────────────
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """将 FastAPI 抛出的 HTTPException 转换为业务标准 JSON 响应。

        业务错误码约定：
          4002 → 未登录 / Token 失效（对应 HTTP 401）
          4003 → 权限不足（对应 HTTP 403）
          4004 → 资源不存在（对应 HTTP 404）
          4001 → 其他客户端错误（对应其余 4xx）

        所有响应均返回 HTTP 200，由前端根据 code 字段判断业务状态。
        """
        if exc.status_code == 401:
            return JSONResponse(status_code=200, content=error_response(4002, str(exc.detail)))
        if exc.status_code == 403:
            return JSONResponse(status_code=200, content=error_response(4003, str(exc.detail)))
        if exc.status_code == 404:
            return JSONResponse(status_code=200, content=error_response(4004, str(exc.detail)))
        return JSONResponse(status_code=200, content=error_response(4001, str(exc.detail)))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """捕获所有未处理的异常，返回通用服务器错误响应（code=5000）。"""
        return JSONResponse(status_code=200, content=error_response(5000, "服务器内部错误"))

    return app


# 创建全局应用实例，供 uvicorn 等 ASGI 服务器直接引用
app = create_app()
