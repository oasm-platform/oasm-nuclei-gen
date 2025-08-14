"""
RAG Engine for retrieving and generating Nuclei templates using similar templates
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from app.services.vector_db import VectorDBService

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_env_config()
        self.vector_db = VectorDBService(self.config.get("vector_db", {}))
        self.initialized = False
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            "vector_db": {
                "type": os.getenv("VECTOR_DB_TYPE", "chromadb"),
                "mode": os.getenv("VECTOR_DB_MODE", "persistent"),
                "persist_directory": os.getenv("VECTOR_DB_PERSIST_DIRECTORY", "./chroma_db"),
                "collection_name": os.getenv("VECTOR_DB_COLLECTION_NAME", "nuclei_templates"),
                "embedding_model": os.getenv("VECTOR_DB_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
                "chunk_size": int(os.getenv("VECTOR_DB_CHUNK_SIZE", "1000")),
                "chunk_overlap": int(os.getenv("VECTOR_DB_CHUNK_OVERLAP", "200"))
            },
            "rag": {
                "max_retrieved_docs": int(os.getenv("RAG_MAX_RETRIEVED_DOCS", "5")),
                "similarity_threshold": float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7")),
                "search_type": os.getenv("RAG_SEARCH_TYPE", "similarity")
            },
            "nuclei": {
                "templates_dir": os.getenv("NUCLEI_TEMPLATES_DIR", "rag_data/nuclei_templates")
            }
        }
    
    async def initialize(self):
        if self.initialized:
            return
        
        try:
            await self.vector_db.initialize()
            self.initialized = True
            logger.info("RAG Engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Engine: {e}")
            raise
    
    async def retrieve_similar_templates(
        self,
        query: str,
        max_results: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        if not self.initialized:
            await self.initialize()
        
        max_results = max_results or self.config.get("rag", {}).get("max_retrieved_docs", 5)
        similarity_threshold = similarity_threshold or self.config.get("rag", {}).get("similarity_threshold", 0.7)
        
        try:
            results = await self.vector_db.search_similar(
                query=query,
                max_results=max_results,
                similarity_threshold=similarity_threshold
            )
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving similar templates: {e}")
            return []
    
    def format_retrieval_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        if not retrieved_docs:
            return "No similar templates found."
        
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            metadata = doc.get("metadata", {})
            similarity = doc.get("similarity", 0)
            content = doc.get("content", "")
            
            template_info = f"""
Template {i+1} (Similarity: {similarity:.2f}):
- ID: {metadata.get('template_id', 'unknown')}
- Name: {metadata.get('name', 'Unknown')}
- Severity: {metadata.get('severity', 'Unknown')}
- Author: {metadata.get('author', 'Unknown')}
- Tags: {metadata.get('tags', [])}
- Description: {metadata.get('description', 'No description')}

Template Content:
```yaml
{content[:800]}{'...' if len(content) > 800 else ''}
```
"""
            context_parts.append(template_info)
        
        return "\n" + "="*80 + "\n".join(context_parts)

    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.initialized:
            await self.initialize()
        
        return await self.vector_db.get_collection_stats()
    
    async def reload_templates(self, templates_dir: Optional[Path] = None) -> int:
        if not self.initialized:
            await self.initialize()
        
        if not templates_dir:
            templates_dir = Path(self.config.get("nuclei", {}).get("templates_dir", "./rag_data/nuclei_templates"))
        
        # Clear existing collection
        await self.vector_db.delete_collection()
        await self.vector_db.initialize()
        
        # Reload templates
        count = await self.vector_db.bulk_load_templates(templates_dir)
        
        return count