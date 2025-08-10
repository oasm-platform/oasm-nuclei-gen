"""
Main entry point of the Nuclei AI Agent Template Generator
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
from app.core.rag_engine import RAGEngine

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
    logger.info("Starting Nuclei AI Agent Template Generator")
    
    # Initialize RAG engine
    try:
        rag_engine = RAGEngine()
        await rag_engine.initialize()
        app.state.rag_engine = rag_engine
        logger.info("RAG engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG engine: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Nuclei AI Agent Template Generator")


app = FastAPI(
    title=os.getenv("APP_NAME", "Nuclei AI Agent Template Generator"),
    description="AI-powered Nuclei template generation and validation service",
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

app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


@app.get("/health")
async def health_check():
    return {
        "message": os.getenv("APP_NAME", "Nuclei AI Agent Template Generator"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "running",
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
