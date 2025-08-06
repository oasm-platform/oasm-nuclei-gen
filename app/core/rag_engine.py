"""
RAG Engine for retrieving and generating Nuclei templates using similar templates
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from app.services.vector_db import VectorDBService


logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.vector_db = VectorDBService(self.config.get("vector_db", {}))
        self.initialized = False
    
    def _load_default_config(self) -> Dict[str, Any]:
        config_path = Path("config/config.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            "vector_db": {
                "type": "chromadb",
                "persist_directory": "./chroma_db",
                "collection_name": "nuclei_templates",
                "embedding_model": "text-embedding-ada-002",
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            "rag": {
                "max_retrieved_docs": 5,
                "similarity_threshold": 0.7,
                "search_type": "similarity"
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
            
            logger.info(f"Retrieved {len(results)} similar templates for query: {query[:100]}...")
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
    
    async def enhance_query_with_context(
        self,
        original_query: str,
        vulnerability_type: Optional[str] = None,
        severity: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        enhanced_query_parts = [original_query]
        
        if vulnerability_type:
            enhanced_query_parts.append(f"vulnerability type: {vulnerability_type}")
        
        if severity:
            enhanced_query_parts.append(f"severity: {severity}")
        
        if tags:
            enhanced_query_parts.append(f"tags: {', '.join(tags)}")
        
        enhanced_query = " ".join(enhanced_query_parts)
        
        # Retrieve similar templates
        similar_templates = await self.retrieve_similar_templates(enhanced_query)
        
        return enhanced_query, similar_templates
    
    async def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        if not self.initialized:
            await self.initialize()
        
        # This is a simplified search by template ID
        # In a real implementation, you might want to index by ID specifically
        try:
            results = await self.vector_db.search_similar(
                query=f"id:{template_id}",
                max_results=1,
                similarity_threshold=0.9
            )
            
            if results:
                return results[0]
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving template by ID {template_id}: {e}")
            return None
    
    async def get_templates_by_severity(self, severity: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.initialized:
            await self.initialize()
        
        try:
            results = await self.vector_db.search_similar(
                query=f"severity:{severity}",
                max_results=max_results,
                similarity_threshold=0.5
            )
            
            # Filter by actual severity in metadata
            filtered_results = [
                result for result in results
                if result.get("metadata", {}).get("severity", "").lower() == severity.lower()
            ]
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error retrieving templates by severity {severity}: {e}")
            return []
    
    async def get_templates_by_tags(self, tags: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.initialized:
            await self.initialize()
        
        try:
            query = " ".join(tags)
            results = await self.vector_db.search_similar(
                query=query,
                max_results=max_results,
                similarity_threshold=0.5
            )
            
            # Filter by actual tags in metadata
            filtered_results = []
            for result in results:
                template_tags = result.get("metadata", {}).get("tags", [])
                if any(tag.lower() in [t.lower() for t in template_tags] for tag in tags):
                    filtered_results.append(result)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error retrieving templates by tags {tags}: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.initialized:
            await self.initialize()
        
        return await self.vector_db.get_collection_stats()
    
    async def reload_templates(self, templates_dir: Optional[Path] = None) -> int:
        if not self.initialized:
            await self.initialize()
        
        if not templates_dir:
            templates_dir = Path(self.config.get("nuclei", {}).get("templates_dir", "./rag_data/nuclei-templates"))
        
        # Clear existing collection
        await self.vector_db.delete_collection()
        await self.vector_db.initialize()
        
        # Reload templates
        count = await self.vector_db.bulk_load_templates(templates_dir)
        logger.info(f"Reloaded {count} templates into RAG engine")
        
        return count