"""
Environment-based data ingestion script for loading Nuclei templates into ChromaDB
"""
import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.vector_db import VectorDBService

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def load_env_config() -> dict:
    """Load configuration from environment variables"""
    logger.info("Loading configuration from environment variables")
    
    config = {
        "app": {
            "name": os.getenv("APP_NAME", "Nuclei AI Agent Template Generator"),
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "debug": os.getenv("APP_DEBUG", "false").lower() == "true",
            "host": os.getenv("APP_HOST", "0.0.0.0"),
            "port": int(os.getenv("APP_PORT", "8000"))
        },
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", "gemini"),
            "model": os.getenv("LLM_MODEL", "gemini-2.0-flash-exp"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
            "timeout": int(os.getenv("LLM_TIMEOUT", "30"))
        },
        "vector_db": {
            "type": os.getenv("VECTOR_DB_TYPE", "chromadb"),
            "mode": os.getenv("VECTOR_DB_MODE", "client"),
            "host": os.getenv("VECTOR_DB_HOST", "localhost"),
            "port": int(os.getenv("VECTOR_DB_PORT", "8001")),
            "collection_name": os.getenv("VECTOR_DB_COLLECTION_NAME", "nuclei_templates"),
            "embedding_model": os.getenv("VECTOR_DB_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "chunk_size": int(os.getenv("VECTOR_DB_CHUNK_SIZE", "1000")),
            "chunk_overlap": int(os.getenv("VECTOR_DB_CHUNK_OVERLAP", "200"))
        },
        "nuclei": {
            "binary_path": os.getenv("NUCLEI_BINARY_PATH", "nuclei"),
            "timeout": int(os.getenv("NUCLEI_TIMEOUT", "30")),
            "validate_args": os.getenv("NUCLEI_VALIDATE_ARGS", "--validate,--verbose").split(","),
            "templates_dir": os.getenv("NUCLEI_TEMPLATES_DIR", "rag_data/nuclei_templates")
        },
        "rag": {
            "max_retrieved_docs": int(os.getenv("RAG_MAX_RETRIEVED_DOCS", "5")),
            "similarity_threshold": float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7")),
            "search_type": os.getenv("RAG_SEARCH_TYPE", "similarity")
        }
    }
    
    return config


async def wait_for_chromadb(host: str, port: int, timeout: int = 60):
    """Wait for ChromaDB to be available"""
    import time
    import socket
    
    logger.info(f"Waiting for ChromaDB at {host}:{port}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info("ChromaDB is available!")
                return True
                
        except Exception as e:
            logger.debug(f"Connection attempt failed: {e}")
        
        logger.info("ChromaDB not ready, waiting 5 seconds...")
        time.sleep(5)
    
    logger.error(f"ChromaDB not available after {timeout} seconds")
    return False


async def ingest_with_retry(templates_dir: Path, config: dict, max_retries: int = 3):
    """Ingest data with retry logic"""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Ingestion attempt {attempt + 1}/{max_retries}")
            
            # Initialize vector database service
            vector_db_service = VectorDBService(config.get("vector_db", {}))
            
            # Wait for ChromaDB if in client mode
            vector_config = config.get("vector_db", {})
            if vector_config.get("mode") == "client":
                host = vector_config.get("host", "localhost")
                port = vector_config.get("port", 8001)
                
                if not await wait_for_chromadb(host, port):
                    raise Exception("ChromaDB not available")
            
            await vector_db_service.initialize()
            
            # Load templates
            count = await vector_db_service.bulk_load_templates(templates_dir)
            logger.info(f"Successfully ingested {count} templates")
            
            return count
            
        except Exception as e:
            logger.error(f"Ingestion attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            
            logger.info("Retrying in 10 seconds...")
            await asyncio.sleep(10)
    
    return 0


async def main():
    parser = argparse.ArgumentParser(description="Environment-based Nuclei templates ingestion")
    parser.add_argument(
        "--templates-dir", 
        type=Path,
        default=Path("rag_data/nuclei_templates"),
        help="Path to Nuclei templates directory"
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=60,
        help="Seconds to wait for ChromaDB availability"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum ingestion retry attempts"
    )
    
    args = parser.parse_args()
    
    try:
        # Load environment-based configuration
        config = await load_env_config()
        if not config:
            logger.error("Failed to load configuration")
            return 1
        
        # Check if templates directory exists
        if not args.templates_dir.exists():
            logger.error(f"Templates directory not found: {args.templates_dir}")
            logger.info("Make sure the templates directory exists")
            return 1
        
        # Ingest with retry logic
        count = await ingest_with_retry(
            templates_dir=args.templates_dir,
            config=config,
            max_retries=args.max_retries
        )
        
        if count > 0:
            logger.info(f"Ingestion completed successfully: {count} templates")
            return 0
        else:
            logger.error("No templates were ingested")
            return 1
            
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)