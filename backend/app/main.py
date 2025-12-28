from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.response import error_response
from app.db.init_db import init_db
from app.routers import analysis, article, behavior, comment, interaction, recommend, user


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI app instance.
    """

    settings = get_settings()
    app = FastAPI(title="Blog Platform API")

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

    @app.on_event("startup")
    def startup_event() -> None:
        """Initialize database tables on application startup.

        Returns:
            None: No return value.
        """

        init_db()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with unified response format.

        Args:
            request (Request): FastAPI request object.
            exc (HTTPException): Raised HTTP exception.

        Returns:
            JSONResponse: Unified error response.
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
        """Handle unexpected exceptions.

        Args:
            request (Request): FastAPI request object.
            exc (Exception): Raised exception.

        Returns:
            JSONResponse: Unified error response.
        """

        return JSONResponse(status_code=200, content=error_response(5000, "服务器内部错误"))

    return app


app = create_app()
