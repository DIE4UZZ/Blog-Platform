from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.core.response import error_response
from backend.app.db.init_db import init_db
from backend.app.routers import (
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
    """创建并配置 FastAPI 应用。"""

    settings = get_settings()
    app = FastAPI(title="Blog Platform API")
    upload_dir = Path("backend/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(user.router, prefix="/api")
    app.include_router(article.router, prefix="/api")
    app.include_router(interaction.router, prefix="/api")
    app.include_router(comment.router, prefix="/api")
    app.include_router(behavior.router, prefix="/api")
    app.include_router(recommend.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(social.router, prefix="/api")
    app.include_router(library.router, prefix="/api")
    app.include_router(rank.router, prefix="/api")
    app.include_router(upload.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    @app.on_event("startup")
    def startup_event() -> None:
        """应用启动时初始化数据库。"""

        init_db()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """统一处理 HTTP 异常并转换为标准响应。"""

        if exc.status_code == 401:
            return JSONResponse(status_code=200, content=error_response(4002, str(exc.detail)))
        if exc.status_code == 403:
            return JSONResponse(status_code=200, content=error_response(4003, str(exc.detail)))
        if exc.status_code == 404:
            return JSONResponse(status_code=200, content=error_response(4004, str(exc.detail)))
        return JSONResponse(status_code=200, content=error_response(4001, str(exc.detail)))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """统一处理未捕获异常。"""

        return JSONResponse(status_code=200, content=error_response(5000, "服务器内部错误"))

    return app


app = create_app()
