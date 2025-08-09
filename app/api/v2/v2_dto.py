"""
DTOs for API v2 endpoints
Contains Pydantic models for all API v2 endpoints with enhanced validation and v2 features
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class SeverityLevel(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TemplateMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class VectorDBType(str, Enum):
    CHROMADB = "chromadb"
    PINECONE = "pinecone"
    FAISS = "faiss"


class VectorDBMode(str, Enum):
    CLIENT = "client"
    EMBEDDED = "embedded"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


# Enhanced Request DTOs for v2
class GetTemplatesBySeverityRequest(BaseModel):
    severity: SeverityLevel = Field(..., description="Security severity level")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of templates to return")
    include_metadata: bool = Field(default=True, description="Include enhanced v2 metadata")
    filter_options: Optional[Dict[str, Any]] = Field(None, description="Additional v2 filtering options")


class GetTemplatesByTagsRequest(BaseModel):
    tags: List[str] = Field(..., min_length=1, description="List of tags to filter by")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of templates to return")
    match_mode: str = Field(default="any", description="Tag matching mode: any, all")
    include_metadata: bool = Field(default=True, description="Include enhanced v2 metadata")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if not v:
            raise ValueError('At least one tag is required')
        for tag in v:
            if not isinstance(tag, str) or len(tag.strip()) == 0:
                raise ValueError('All tags must be non-empty strings')
            if len(tag.strip()) > 50:
                raise ValueError('Tag length cannot exceed 50 characters')
        return [tag.strip() for tag in v]
    
    @field_validator('match_mode')
    @classmethod
    def validate_match_mode(cls, v):
        valid_modes = ['any', 'all']
        if v not in valid_modes:
            raise ValueError(f'Match mode must be one of: {", ".join(valid_modes)}')
        return v


# Enhanced Response DTOs for v2
class TemplateInfoV2(BaseModel):
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    author: List[str] = Field(..., description="Template authors")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    description: str = Field(..., description="Vulnerability description")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    reference: Optional[List[str]] = Field(None, description="References")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    classification: Optional[Dict[str, Any]] = Field(None, description="V2 enhanced classification")
    confidence_score: Optional[float] = Field(None, description="V2 confidence score")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")


class V2Metadata(BaseModel):
    api_version: str = Field(default="v2", description="API version")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    enhanced_features: List[str] = Field(default=[], description="List of v2 enhanced features used")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")


class GetTemplatesBySeverityResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    severity: SeverityLevel = Field(..., description="Requested severity level")
    templates: List[TemplateInfoV2] = Field(..., description="List of matching templates")
    total_results: int = Field(..., ge=0, description="Total number of results")
    metadata: V2Metadata = Field(default_factory=V2Metadata, description="V2 enhanced metadata")
    filter_info: Dict[str, Any] = Field(default={}, description="Applied filter information")
    
    @field_validator('templates')
    @classmethod
    def validate_templates(cls, v):
        if not isinstance(v, list):
            raise ValueError('Templates must be a list')
        return v


class SystemInfoV2(BaseModel):
    nuclei_version: Optional[str] = Field(None, description="Nuclei version")
    nuclei_available: bool = Field(..., description="Whether Nuclei is available")
    rag_initialized: bool = Field(..., description="Whether RAG engine is initialized")
    templates_count: Optional[int] = Field(None, description="Number of loaded templates")
    last_update: Optional[str] = Field(None, description="Last update timestamp")
    system_health: str = Field(default="unknown", description="Overall system health status")
    performance_stats: Optional[Dict[str, Any]] = Field(None, description="V2 performance statistics")
    resource_usage: Optional[Dict[str, Any]] = Field(None, description="V2 resource usage metrics")


class GetAgentStatusResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    status: str = Field(..., description="Overall agent status")
    details: SystemInfoV2 = Field(..., description="Detailed system information")
    timestamp: Optional[str] = Field(None, description="Status check timestamp")
    system_info: Dict[str, Any] = Field(default={}, description="Additional v2 system information")
    uptime: Optional[float] = Field(None, description="System uptime in seconds")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['healthy', 'degraded', 'error']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class CollectionStatsV2(BaseModel):
    collection_name: str = Field(..., description="Collection name")
    total_documents: int = Field(..., ge=0, description="Total number of documents")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    index_status: Optional[str] = Field(None, description="Index status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    optimization_level: Optional[str] = Field(None, description="V2 optimization level")
    query_performance: Optional[Dict[str, Any]] = Field(None, description="V2 query performance metrics")


class GetRAGStatsResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    collection_stats: CollectionStatsV2 = Field(..., description="Collection statistics")
    performance_metrics: Dict[str, Any] = Field(default={}, description="V2 enhanced performance metrics")
    initialization_status: bool = Field(..., description="RAG initialization status")
    last_update: Optional[str] = Field(None, description="Last update timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


class GetTemplatesByTagsResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    tags: List[str] = Field(..., description="Requested tags")
    templates: List[TemplateInfoV2] = Field(..., description="List of matching templates")
    total_results: int = Field(..., ge=0, description="Total number of results")
    search_metadata: Dict[str, Any] = Field(default={}, description="V2 enhanced search metadata")
    tag_analysis: Optional[Dict[str, Any]] = Field(None, description="V2 tag analysis results")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if not v:
            raise ValueError('At least one tag is required')
        return v


class ReloadTemplatesResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    success: bool = Field(..., description="Whether reload was successful")
    templates_loaded: int = Field(..., ge=0, description="Number of templates loaded")
    message: str = Field(..., description="Status message")
    performance_metrics: Dict[str, Any] = Field(default={}, description="V2 reload performance metrics")
    processing_mode: str = Field(default="enhanced_v2", description="Processing mode used")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        return v.strip()


class ClearRAGCollectionResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    status: str = Field(..., description="Operation status")
    collection_name: Optional[str] = Field(None, description="Collection name that was cleared")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if any")
    cleared_count: Optional[int] = Field(None, ge=0, description="Number of items cleared")
    cleanup_metadata: Dict[str, Any] = Field(default={}, description="V2 cleanup metadata")
    cleanup_mode: str = Field(default="enhanced_v2", description="Cleanup mode used")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['success', 'failed', 'partial']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


# Enhanced Common DTOs for v2
class ValidationResultV2(BaseModel):
    is_valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")
    validation_mode: Optional[str] = Field(None, description="V2 validation mode used")
    confidence_score: Optional[float] = Field(None, description="V2 validation confidence")


class ErrorResponseV2(BaseModel):
    api_version: str = Field(default="v2", description="API version identifier")
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_code: Optional[str] = Field(None, description="V2 specific error code")
    suggested_action: Optional[str] = Field(None, description="V2 suggested action for resolution")


class NucleiInfoV2(BaseModel):
    name: str = Field(..., description="Template name")
    author: List[str] = Field(..., description="Template authors")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    description: str = Field(..., description="Vulnerability description")
    reference: Optional[List[str]] = Field(None, description="References")
    classification: Optional[Dict[str, Any]] = Field(None, description="Enhanced v2 classification info")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional v2 metadata")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    confidence_rating: Optional[float] = Field(None, description="V2 confidence rating")


class HttpRequestV2(BaseModel):
    method: TemplateMethod = Field(default=TemplateMethod.GET)
    path: List[str] = Field(..., description="Request paths")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    body: Optional[str] = Field(None, description="Request body")
    raw: Optional[List[str]] = Field(None, description="Raw HTTP requests")
    v2_enhancements: Optional[Dict[str, Any]] = Field(None, description="V2 specific enhancements")


class MatcherV2(BaseModel):
    type: str = Field(..., description="Matcher type (word, regex, status, etc.)")
    words: Optional[List[str]] = Field(None, description="Words to match")
    regex: Optional[List[str]] = Field(None, description="Regex patterns")
    status: Optional[List[int]] = Field(None, description="Status codes")
    condition: Optional[str] = Field(None, description="Matching condition")
    part: Optional[str] = Field(None, description="Part to match (body, header, etc.)")
    case_insensitive: Optional[bool] = Field(None, description="Case insensitive matching")
    confidence_level: Optional[float] = Field(None, description="V2 confidence level")


class ExtractorV2(BaseModel):
    type: str = Field(..., description="Extractor type")
    regex: Optional[List[str]] = Field(None, description="Regex patterns")
    part: Optional[str] = Field(None, description="Part to extract from")
    group: Optional[int] = Field(None, description="Regex group")
    precision_mode: Optional[str] = Field(None, description="V2 extraction precision mode")


class NucleiTemplateV2(BaseModel):
    id: str = Field(..., description="Template ID")
    info: NucleiInfoV2 = Field(..., description="Enhanced template info")
    http: Optional[List[HttpRequestV2]] = Field(None, description="Enhanced HTTP requests")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    matchers: Optional[List[MatcherV2]] = Field(None, description="Enhanced response matchers")
    extractors: Optional[List[ExtractorV2]] = Field(None, description="Enhanced data extractors")
    matchers_condition: Optional[str] = Field(None, description="Matchers condition")
    v2_metadata: Optional[Dict[str, Any]] = Field(None, description="V2 specific metadata")


class TargetInfoV2(BaseModel):
    url: str = Field(..., description="Target URL", min_length=1, max_length=2000)
    method: TemplateMethod = Field(default=TemplateMethod.GET)
    parameters: Optional[List[str]] = Field(None, description="URL/form parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    cookies: Optional[Dict[str, str]] = Field(None, description="Cookies")
    security_context: Optional[Dict[str, Any]] = Field(None, description="V2 security context")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('URL cannot be empty')
        
        v = v.strip()
        
        # Basic URL validation
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        
        return v


class TemplateGenerationRequestV2(BaseModel):
    vulnerability_description: str = Field(..., min_length=10, max_length=1000, description="Description of the vulnerability")
    target_info: TargetInfoV2 = Field(..., description="Enhanced target information")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    author: Optional[str] = Field(None, description="Template author")
    references: Optional[List[str]] = Field(None, description="References")
    generation_mode: Optional[str] = Field("enhanced_v2", description="V2 generation mode")
    quality_threshold: Optional[float] = Field(0.8, description="V2 quality threshold")


class TemplateGenerationResponseV2(BaseModel):
    success: bool = Field(..., description="Generation success status")
    template_id: str = Field(..., description="Generated template ID")
    generated_template: str = Field(..., description="Generated YAML template")
    validation_result: ValidationResultV2 = Field(..., description="Enhanced template validation result")
    retrieval_context: Optional[List[str]] = Field(None, description="Retrieved similar templates")
    generation_metadata: Dict[str, Any] = Field(default={}, description="Enhanced generation metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    v2_enhancements: Optional[Dict[str, Any]] = Field(None, description="V2 specific enhancements applied")


class TemplateValidationRequestV2(BaseModel):
    template_content: str = Field(..., min_length=10, max_length=50000, description="YAML template content")
    validate_syntax_only: bool = Field(default=False, description="Only validate YAML syntax")
    validation_level: Optional[str] = Field("standard", description="V2 validation level: basic, standard, strict")
    include_suggestions: bool = Field(default=True, description="Include v2 improvement suggestions")

    @field_validator('template_content')
    @classmethod
    def validate_template_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Template content cannot be empty')
        
        v = v.strip()
        
        # Basic YAML structure validation
        if not v.startswith('id:') and 'id:' not in v:
            raise ValueError('Template must contain an "id" field')
        
        if not v.startswith('info:') and 'info:' not in v:
            raise ValueError('Template must contain an "info" field')
        
        return v
    
    @field_validator('validation_level')
    @classmethod
    def validate_validation_level(cls, v):
        valid_levels = ['basic', 'standard', 'strict']
        if v not in valid_levels:
            raise ValueError(f'Validation level must be one of: {", ".join(valid_levels)}')
        return v


class TemplateValidationResponseV2(BaseModel):
    validation_result: ValidationResultV2 = Field(..., description="Enhanced validation result")
    template_id: Optional[str] = Field(None, description="Extracted template ID")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    suggestions: Optional[List[str]] = Field(None, description="V2 improvement suggestions")
    quality_score: Optional[float] = Field(None, description="V2 template quality score")


class RAGSearchRequestV2(BaseModel):
    query: str = Field(..., min_length=5, max_length=500, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    search_mode: Optional[str] = Field("hybrid", description="V2 search mode: semantic, keyword, hybrid")
    ranking_algorithm: Optional[str] = Field("enhanced_v2", description="V2 ranking algorithm")
    
    @field_validator('search_mode')
    @classmethod
    def validate_search_mode(cls, v):
        valid_modes = ['semantic', 'keyword', 'hybrid']
        if v not in valid_modes:
            raise ValueError(f'Search mode must be one of: {", ".join(valid_modes)}')
        return v


class RAGSearchResponseV2(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="Enhanced search results")
    query: str = Field(..., description="Original query")
    total_results: int = Field(..., description="Total number of results")
    search_metadata: Dict[str, Any] = Field(default={}, description="V2 enhanced search metadata")
    query_analysis: Optional[Dict[str, Any]] = Field(None, description="V2 query analysis")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="V2 search performance metrics")


class UpdateRAGDataRequestV2(BaseModel):
    vector_db: Optional[Dict[str, Any]] = Field(None, description="Vector DB configuration")
    llm: Optional[Dict[str, Any]] = Field(None, description="LLM configuration")
    nuclei: Optional[Dict[str, Any]] = Field(None, description="Nuclei configuration")
    rag: Optional[Dict[str, Any]] = Field(None, description="RAG configuration")
    force_update: bool = Field(default=False, description="Force update even if templates exist")
    optimization_level: Optional[str] = Field("standard", description="V2 optimization level")
    parallel_processing: bool = Field(default=True, description="Enable v2 parallel processing")


class UpdateRAGDataResponseV2(BaseModel):
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update result message")
    templates_cleared: int = Field(default=0, description="Number of templates cleared")
    templates_downloaded: int = Field(default=0, description="Number of templates downloaded")
    templates_loaded: int = Field(default=0, description="Number of templates loaded to database")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default={}, description="Enhanced v2 metadata")
    processing_enhancements: Optional[str] = Field(None, description="V2 processing enhancements applied")
    performance_summary: Optional[Dict[str, Any]] = Field(None, description="V2 performance summary")