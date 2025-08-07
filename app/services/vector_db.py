"""
Vector database service for storing and retrieving Nuclei template embeddings
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

import chromadb
from chromadb.config import Settings
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)


class VectorDBService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection = None
        self.embeddings = None
        self.text_splitter = None
        self._setup_embeddings()
        self._setup_text_splitter()
    
    """

    Setup embeddings based on the configuration
    """
    def _setup_embeddings(self):
        embedding_model = self.config.get("embedding_model", "text-embedding-ada-002")
        
        if embedding_model.startswith("text-embedding"):
            # Load OpenAI API key from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
            
            self.embeddings = OpenAIEmbeddings(model=embedding_model, openai_api_key=api_key)
        else:
            self.embeddings = SentenceTransformer(embedding_model)
    
    """
    Setup text splitter based on the configuration
    """
    def _setup_text_splitter(self):
        chunk_size = self.config.get("chunk_size", 1000)
        chunk_overlap = self.config.get("chunk_overlap", 200)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    """
    Initialize the vector database based on the configuration
    """
    async def initialize(self):
        db_type = self.config.get("type", "chromadb")
        
        if db_type == "chromadb":
            await self._initialize_chromadb()
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
    
    """
    Initialize the ChromaDB vector database
    """
    async def _initialize_chromadb(self):
        collection_name = self.config.get("collection_name", "nuclei_templates")
        
        # Check if we should use HTTP client (Docker mode) or embedded mode
        chromadb_mode = self.config.get("mode", os.getenv("CHROMADB_MODE", "embedded"))
        
        if chromadb_mode == "client":
            # HTTP Client mode for Docker
            host = self.config.get("host", os.getenv("CHROMADB_HOST", "localhost"))
            port = self.config.get("port", int(os.getenv("CHROMADB_PORT", "8001")))
            
            logger.info(f"Connecting to ChromaDB server at {host}:{port}")
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        else:
            # Embedded mode (original implementation)
            persist_directory = self.config.get("persist_directory", "./chroma_db")
            
            # Ensure directory exists
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Using embedded ChromaDB at {persist_directory}")
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {collection_name}")
    
    """
    Add documents to the vector database
    """
    async def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        if not self.collection:
            raise RuntimeError("Vector database not initialized")
        
        processed_docs = []
        for doc in documents:
            chunks = self._split_document(doc)
            processed_docs.extend(chunks)
        
        if not processed_docs:
            return 0
        
        # Process in smaller batches to avoid ChromaDB limits
        batch_size = 5000  # Safe batch size for ChromaDB
        total_added = 0
        
        for i in range(0, len(processed_docs), batch_size):
            batch_docs = processed_docs[i:i + batch_size]
            
            # Generate embeddings for batch
            texts = [doc["content"] for doc in batch_docs]
            if hasattr(self.embeddings, 'embed_documents'):
                embeddings = self.embeddings.embed_documents(texts)
            else:
                embeddings = self.embeddings.encode(texts).tolist()
            
            # Add batch to collection
            ids = [doc["id"] for doc in batch_docs]
            metadatas = [doc["metadata"] for doc in batch_docs]
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            total_added += len(batch_docs)
            logger.info(f"Added batch {i//batch_size + 1}: {len(batch_docs)} chunks ({total_added}/{len(processed_docs)} total)")
        
        logger.info(f"Successfully added {total_added} document chunks to vector database")
        return total_added
    
    """
    Split document into chunks
    """
    def _split_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = document.get("content", "")
        metadata = document.get("metadata", {})
        doc_id = document.get("id", "unknown")
        file_path = metadata.get("file_path", "")
        
        chunks = self.text_splitter.split_text(content)
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            # Create unique ID using file path hash to avoid duplicates
            import hashlib
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            chunk_id = f"{doc_id}_{file_hash}_chunk_{i}"
            
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_doc_id": doc_id
            }
            
            processed_chunks.append({
                "id": chunk_id,
                "content": chunk,
                "metadata": chunk_metadata
            })
        
        return processed_chunks
    
    """
    Search for similar documents
    """
    async def search_similar(
        self,
        query: str,
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        if not self.collection:
            raise RuntimeError("Vector database not initialized")
        
        # Generate query embedding
        if hasattr(self.embeddings, 'embed_query'):
            query_embedding = self.embeddings.embed_query(query)
        else:
            query_embedding = self.embeddings.encode([query])[0].tolist()
        
        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Filter by similarity threshold
        filtered_results = []
        for i, distance in enumerate(results["distances"][0]):
            similarity = 1 - distance  # Convert distance to similarity
            if similarity >= similarity_threshold:
                filtered_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": similarity
                })
        
        return filtered_results
    
    """
    Get collection statistics
    """
    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.collection:
            return {"error": "Collection not initialized"}
        
        count = self.collection.count()
        return {
            "total_documents": count,
            "collection_name": self.collection.name
        }
    
    """
    Delete the collection
    """
    async def delete_collection(self):
        if self.collection:
            self.client.delete_collection(self.collection.name)
            self.collection = None
            logger.info("Collection deleted")
    
    """
    Load a Nuclei template from a file
    """
    def load_nuclei_template(self, template_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                template_data = yaml.safe_load(template_content)
            
            # Extract template information
            template_id = template_data.get("id", template_path.stem)
            info = template_data.get("info", {})
            
            # Create document with ChromaDB-compatible metadata
            author = info.get("author", [])
            tags = info.get("tags", [])
            reference = info.get("reference", [])
            classification = info.get("classification", {})
            
            document = {
                "id": template_id,
                "content": template_content,
                "metadata": {
                    "template_id": template_id,
                    "name": info.get("name", ""),
                    "author": ", ".join(author) if isinstance(author, list) else str(author),
                    "severity": info.get("severity", ""),
                    "description": info.get("description", ""),
                    "tags": ", ".join(tags) if isinstance(tags, list) else str(tags),
                    "reference": ", ".join(reference) if isinstance(reference, list) else str(reference),
                    "file_path": str(template_path),
                    "classification": str(classification) if classification else "",
                }
            }
            
            return document
            
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {e}")
            return None
    
    """
    Bulk load Nuclei templates from a directory
    """
    async def bulk_load_templates(self, templates_dir: Path) -> int:
        if not templates_dir.exists():
            logger.error(f"Templates directory not found: {templates_dir}")
            return 0
        
        documents = []
        yaml_files = list(templates_dir.rglob("*.yaml")) + list(templates_dir.rglob("*.yml"))
        
        for template_file in yaml_files:
            document = self.load_nuclei_template(template_file)
            if document:
                documents.append(document)
        
        if documents:
            return await self.add_documents(documents)
        
        return 0