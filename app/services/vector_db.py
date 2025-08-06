"""
Vector database service for storing and retrieving Nuclei template embeddings
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

import chromadb
from chromadb.config import Settings
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
    
    def _setup_embeddings(self):
        embedding_model = self.config.get("embedding_model", "text-embedding-ada-002")
        
        if embedding_model.startswith("text-embedding"):
            self.embeddings = OpenAIEmbeddings(model=embedding_model)
        else:
            self.embeddings = SentenceTransformer(embedding_model)
    
    def _setup_text_splitter(self):
        chunk_size = self.config.get("chunk_size", 1000)
        chunk_overlap = self.config.get("chunk_overlap", 200)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    async def initialize(self):
        db_type = self.config.get("type", "chromadb")
        
        if db_type == "chromadb":
            await self._initialize_chromadb()
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
    
    async def _initialize_chromadb(self):
        persist_directory = self.config.get("persist_directory", "./chroma_db")
        collection_name = self.config.get("collection_name", "nuclei_templates")
        
        # Ensure directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
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
        except ValueError:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {collection_name}")
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        if not self.collection:
            raise RuntimeError("Vector database not initialized")
        
        processed_docs = []
        for doc in documents:
            chunks = self._split_document(doc)
            processed_docs.extend(chunks)
        
        if not processed_docs:
            return 0
        
        # Generate embeddings
        texts = [doc["content"] for doc in processed_docs]
        if hasattr(self.embeddings, 'embed_documents'):
            embeddings = self.embeddings.embed_documents(texts)
        else:
            embeddings = self.embeddings.encode(texts).tolist()
        
        # Add to collection
        ids = [doc["id"] for doc in processed_docs]
        metadatas = [doc["metadata"] for doc in processed_docs]
        
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(processed_docs)} document chunks to vector database")
        return len(processed_docs)
    
    def _split_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = document.get("content", "")
        metadata = document.get("metadata", {})
        doc_id = document.get("id", "unknown")
        
        chunks = self.text_splitter.split_text(content)
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
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
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.collection:
            return {"error": "Collection not initialized"}
        
        count = self.collection.count()
        return {
            "total_documents": count,
            "collection_name": self.collection.name
        }
    
    async def delete_collection(self):
        if self.collection:
            self.client.delete_collection(self.collection.name)
            self.collection = None
            logger.info("Collection deleted")
    
    def load_nuclei_template(self, template_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                template_data = yaml.safe_load(template_content)
            
            # Extract template information
            template_id = template_data.get("id", template_path.stem)
            info = template_data.get("info", {})
            
            # Create document
            document = {
                "id": template_id,
                "content": template_content,
                "metadata": {
                    "template_id": template_id,
                    "name": info.get("name", ""),
                    "author": info.get("author", []),
                    "severity": info.get("severity", ""),
                    "description": info.get("description", ""),
                    "tags": info.get("tags", []),
                    "reference": info.get("reference", []),
                    "file_path": str(template_path),
                    "classification": info.get("classification", {}),
                }
            }
            
            return document
            
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {e}")
            return None
    
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