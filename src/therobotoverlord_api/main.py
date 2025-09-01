"""Main application entry point for The Robot Overlord API."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from therobotoverlord_api.api.admin import router as admin_router
from therobotoverlord_api.api.appeals import router as appeals_router
from therobotoverlord_api.api.appeals_dashboard import (
    router as appeals_dashboard_router,
)
from therobotoverlord_api.api.auth import router as auth_router
from therobotoverlord_api.api.badges import router as badges_router
from therobotoverlord_api.api.flags import router as flags_router
from therobotoverlord_api.api.leaderboard import router as leaderboard_router
from therobotoverlord_api.api.loyalty_score import router as loyalty_router
from therobotoverlord_api.api.messages import router as messages_router
from therobotoverlord_api.api.posts import router as posts_router
from therobotoverlord_api.api.queue import router as queue_router
from therobotoverlord_api.api.rbac import router as rbac_router
from therobotoverlord_api.api.sanctions import router as sanctions_router
from therobotoverlord_api.api.tags import router as tags_router
from therobotoverlord_api.api.topics import router as topics_router
from therobotoverlord_api.api.translations import router as translations_router
from therobotoverlord_api.api.users import router as users_router
from therobotoverlord_api.api.websocket import router as websocket_router
from therobotoverlord_api.auth.dependencies import get_optional_user
from therobotoverlord_api.database.connection import close_database
from therobotoverlord_api.database.connection import db
from therobotoverlord_api.database.connection import init_database
from therobotoverlord_api.database.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="The Robot Overlord API",
        description="A satirical AI-moderated debate platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://therobotoverlord.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(appeals_router, prefix="/api/v1")
    app.include_router(appeals_dashboard_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(badges_router, prefix="/api/v1")
    app.include_router(flags_router, prefix="/api/v1")
    app.include_router(leaderboard_router, prefix="/api/v1")
    app.include_router(loyalty_router, prefix="/api/v1")
    app.include_router(messages_router, prefix="/api/v1")
    app.include_router(posts_router, prefix="/api/v1")
    app.include_router(queue_router, prefix="/api/v1")
    app.include_router(rbac_router, prefix="/api/v1")
    app.include_router(sanctions_router, prefix="/api/v1")
    app.include_router(tags_router, prefix="/api/v1")
    app.include_router(topics_router, prefix="/api/v1")
    app.include_router(translations_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(websocket_router)

    @app.get("/health")
    async def health_check(
        user: Annotated[User | None, Depends(get_optional_user)] = None,
    ):
        """Health check endpoint."""

        db_healthy = await db.health_check()
        pool_stats = await db.get_pool_stats()

        return {
            "status": "ok" if db_healthy else "error",
            "database": {
                "healthy": db_healthy,
                "pool": pool_stats,
            },
        }

    return app


app = create_app()


def main():
    """Main entry point - creates and returns the app instance."""
    return create_app()


if __name__ == "__main__":
    # Only run uvicorn when called directly, not when imported
    import uvicorn

    uvicorn.run(
        "therobotoverlord_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
