"""
Main entry point of the Nuclei Template Generator (LLM + RAG)
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import v1_router, TokenAuthMiddleware
from app.core.config_service import ConfigService
from app.core.nuclei_service import NucleiTemplateService


# Get settings from ConfigService
settings = ConfigService.get_settings()

# Configure logging using environment variables (keeping for logging setup)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_file_path = os.getenv("LOG_FILE_PATH", "logs/app.log")
# Ensure logs directory exists
Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
# Suppress watchfiles INFO messages
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Nuclei Template Generator (LLM + RAG)")
    
    # Initialize Nuclei Template Service
    try:
        nuclei_service = NucleiTemplateService()
        await nuclei_service.rag_engine.initialize()
        app.state.nuclei_service = nuclei_service
    except Exception as e:
        logger.error(f"Failed to initialize Nuclei Template Service: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Nuclei Template Generator")


app = FastAPI(
    title=settings.app.name,
    description="🕵️‍♂️ AI Genetate Template Nuclei For Cybersecurity Attack Surface Management (ASM).",
    version=settings.app.version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(
    TokenAuthMiddleware,
    excluded_paths=["/health", "/docs", "/redoc", "/openapi.json"]
)

app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


@app.get("/health")
async def health_check():
    stats = await app.state.nuclei_service.rag_engine.get_collection_stats()
    return {
        "message": settings.app.name,
        "version": settings.app.version,
        "status": "healthy",
        "collection_name": stats.get("collection_name", ""),
        "total_documents": stats.get("total_documents", 0)
    }


if __name__ == "__main__":
    # Get configuration from settings
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
