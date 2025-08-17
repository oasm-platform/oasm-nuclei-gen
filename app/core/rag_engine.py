"""
RAG Engine for retrieving and generating Nuclei templates using similar templates
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config_service import ConfigService
from app.core.vector_db import VectorDBService

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            self.settings = ConfigService.get_settings()
            # Convert Pydantic model to dict for VectorDBService
            vector_db_config = {
                "type": self.settings.vector_db.type,
                "mode": self.settings.vector_db.mode,
                "host": self.settings.vector_db.host,
                "port": self.settings.vector_db.port,
                "collection_name": self.settings.vector_db.collection_name,
                "embedding_model": self.settings.vector_db.embedding_model,
                "chunk_size": self.settings.vector_db.chunk_size,
                "chunk_overlap": self.settings.vector_db.chunk_overlap
            }
            self.vector_db = VectorDBService(vector_db_config)
        else:
            # Legacy support for dict config
            self.settings = None
            self.vector_db = VectorDBService(config.get("vector_db", {}))
        self.initialized = False
    
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
        
        if self.settings:
            max_results = max_results or self.settings.rag.max_retrieved_docs
            similarity_threshold = similarity_threshold or self.settings.rag.similarity_threshold
        else:
            # Legacy defaults
            max_results = max_results or 5
            similarity_threshold = similarity_threshold or 0.7
        
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
            templates_dir = Path(self.settings.nuclei.templates_dir)
        
        # Clear existing collection
        await self.vector_db.delete_collection()
        await self.vector_db.initialize()
        
        # Reload templates
        count = await self.vector_db.bulk_load_templates(templates_dir)
        
        return count