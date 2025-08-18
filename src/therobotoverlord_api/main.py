"""Main application entry point for The Robot Overlord API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from therobotoverlord_api.api.auth import router as auth_router
from therobotoverlord_api.auth.middleware import AuthenticationMiddleware
from therobotoverlord_api.database.connection import close_database
from therobotoverlord_api.database.connection import db
from therobotoverlord_api.database.connection import init_database


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

    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)

    # Include routers
    app.include_router(auth_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
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
