"""
Main entry point of the Nuclei Template Generator (LLM + RAG)
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import router as v1_router
from app.core.nuclei_service import NucleiTemplateService
from app.api.middlewares.auth import TokenAuthMiddleware

# Load environment variables
load_dotenv()


# Configure logging using environment variables
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
    title=os.getenv("APP_NAME", "Nuclei Template Generator"),
    description="🕵️‍♂️ AI Genetate Template Nuclei For Cybersecurity Attack Surface Management (ASM).",
    version=os.getenv("APP_VERSION", "1.0.0"),
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
        "message": os.getenv("APP_NAME", "Nuclei Template Generator"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "healthy",
        "collection_name": stats.get("collection_name", ""),
        "total_documents": stats.get("total_documents", 0)
    }


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("APP_HOST", "localhost")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level=log_level
    )
