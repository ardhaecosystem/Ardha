"""
Main FastAPI application for Ardha backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ardha.api.v1.routes import auth, milestones, projects, tasks
from ardha.core.config import settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Ardha API",
        description="Ardha backend API",
        version="0.1.0",
        debug=settings.debug,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(milestones.router, prefix="/api/v1/milestones")
    app.include_router(tasks.router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "ardha-backend"}
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Welcome to Ardha API",
            "version": "0.1.0",
            "environment": settings.app_env,
        }
    
    return app


# Create FastAPI app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "ardha.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )