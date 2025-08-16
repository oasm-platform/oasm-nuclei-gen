from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings"""
    name: str = Field(default="Nuclei Template Generator", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Application host")
    port: int = Field(default=8000, description="Application port")

    model_config = SettingsConfigDict(env_prefix="APP_")


class LLMSettings(BaseSettings):
    """LLM provider settings"""
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-2.0-flash-exp", description="LLM model")
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_tokens: int = Field(default=2000, description="Maximum tokens")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    model_config = SettingsConfigDict(env_prefix="LLM_")


class VectorDBSettings(BaseSettings):
    """Vector database settings"""
    type: str = Field(default="chromadb", description="Vector database type")
    mode: str = Field(default="client", description="Vector database mode")
    host: str = Field(default="localhost", description="Vector database host")
    port: int = Field(default=8001, description="Vector database port")
    collection_name: str = Field(default="nuclei_templates", description="Collection name")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model")
    chunk_size: int = Field(default=1000, description="Chunk size for text splitting")
    chunk_overlap: int = Field(default=200, description="Chunk overlap")

    model_config = SettingsConfigDict(env_prefix="VECTOR_DB_")


class NucleiSettings(BaseSettings):
    """Nuclei tool settings"""
    binary_path: str = Field(default="nuclei", description="Nuclei binary path")
    timeout: int = Field(default=30, description="Nuclei execution timeout")
    templates_dir: str = Field(default="./rag_data/nuclei_templates", description="Templates directory")
    validate_args: str = Field(default="--validate,--verbose", description="Validation arguments (comma-separated)")

    model_config = SettingsConfigDict(env_prefix="NUCLEI_")

    @property
    def validate_args_list(self) -> List[str]:
        """Get validation arguments as a list"""
        return self.validate_args.split(",")


class RAGSettings(BaseSettings):
    """RAG (Retrieval-Augmented Generation) settings"""
    max_retrieved_docs: int = Field(default=5, description="Maximum retrieved documents")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")
    search_type: str = Field(default="similarity", description="Search type")

    model_config = SettingsConfigDict(env_prefix="RAG_")


class TemplateGenerationSettings(BaseSettings):
    """Template generation settings"""
    max_retries: int = Field(default=3, description="Maximum retries for generation")
    output_format: str = Field(default="yaml", description="Output format")
    include_metadata: bool = Field(default=True, description="Include metadata")

    model_config = SettingsConfigDict(env_prefix="TEMPLATE_")


class Settings(BaseSettings):
    """Main application settings"""
    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    nuclei: NucleiSettings = Field(default_factory=NucleiSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    template_generation: TemplateGenerationSettings = Field(default_factory=TemplateGenerationSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class ConfigService:
    """Configuration service using Pydantic Settings"""
    
    _settings: Settings = None
    
    @classmethod
    def get_settings(cls) -> Settings:
        """Get application settings singleton"""
        if cls._settings is None:
            cls._settings = Settings()
        return cls._settings
    
    @classmethod
    def reload_settings(cls) -> Settings:
        """Reload settings from environment"""
        cls._settings = Settings()
        return cls._settings