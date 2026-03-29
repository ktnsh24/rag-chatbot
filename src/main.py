"""
RAG Chatbot — FastAPI Application Entry Point

This is the main file. It:
1. Creates the FastAPI app
2. Registers routes (chat, documents, health)
3. Configures middleware (logging, CORS, tracing)
4. Sets up the lifespan (startup + shutdown)

Run with:
    poetry run start
    # or
    poetry run uvicorn src.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.routes import chat, documents, health
from src.config import get_settings
from src.monitoring.metrics import MetricsCollector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
        - Log configuration
        - Initialize cloud clients (LLM, vector store, storage, history)
        - Initialize metrics collector
        - Verify connectivity to backend services

    Shutdown:
        - Close open connections
        - Flush metrics
    """
    settings = get_settings()

    # --- Startup ---
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.app_env.value}")
    logger.info(f"Cloud Provider: {settings.cloud_provider.value}")
    logger.info(f"Port: {settings.app_port}")
    logger.info("=" * 60)

    # Initialize metrics
    metrics = MetricsCollector()
    app.state.metrics = metrics
    logger.info("Metrics collector initialized")

    # Initialize cloud-specific backends
    try:
        from src.rag.chain import RAGChain

        rag_chain = await RAGChain.create(settings)
        app.state.rag_chain = rag_chain
        logger.info(f"RAG chain initialized with {settings.cloud_provider.value} backends")
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {e}")
        logger.warning("App will start but chat endpoint will return errors")
        app.state.rag_chain = None

    logger.info("Startup complete — ready to serve requests")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Factory function that creates and configures the FastAPI application.

    Why a factory function?
        - Tests can call create_app() with different settings
        - Avoids global state issues
        - Standard pattern in production FastAPI apps
    """
    settings = get_settings()

    app = FastAPI(
        title="RAG Chatbot API",
        description="Enterprise Retrieval-Augmented Generation chatbot — multi-cloud (AWS + Azure)",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware (order matters — last added = first executed) ---
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ---
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(documents.router, prefix="/api", tags=["Documents"])

    # --- Static files (chat UI) ---
    try:
        app.mount("/static", StaticFiles(directory="src/ui/templates"), name="static")
    except RuntimeError:
        logger.warning("Static files directory not found — chat UI will not be available")

    return app


# Create the app instance (used by uvicorn)
app = create_app()


def run():
    """Entry point for `poetry run start`."""
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.app_env == "dev",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
