"""
DTOs for API v1 endpoints
Contains Pydantic models for all API v1 endpoints including validation schemas
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


# Request DTOs
class GetTemplatesBySeverityRequest(BaseModel):
    severity: SeverityLevel = Field(..., description="Security severity level")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of templates to return")


class GetTemplatesByTagsRequest(BaseModel):
    tags: List[str] = Field(..., min_length=1, description="List of tags to filter by")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of templates to return")
    
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


# Response DTOs
class TemplateInfo(BaseModel):
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    author: List[str] = Field(..., description="Template authors")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    description: str = Field(..., description="Vulnerability description")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    reference: Optional[List[str]] = Field(None, description="References")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class GetTemplatesBySeverityResponse(BaseModel):
    severity: SeverityLevel = Field(..., description="Requested severity level")
    templates: List[TemplateInfo] = Field(..., description="List of matching templates")
    total_results: int = Field(..., ge=0, description="Total number of results")
    
    @field_validator('templates')
    @classmethod
    def validate_templates(cls, v):
        if not isinstance(v, list):
            raise ValueError('Templates must be a list')
        return v


class SystemInfo(BaseModel):
    nuclei_version: Optional[str] = Field(None, description="Nuclei version")
    nuclei_available: bool = Field(..., description="Whether Nuclei is available")
    rag_initialized: bool = Field(..., description="Whether RAG engine is initialized")
    templates_count: Optional[int] = Field(None, description="Number of loaded templates")
    last_update: Optional[str] = Field(None, description="Last update timestamp")


class GetAgentStatusResponse(BaseModel):
    status: str = Field(..., description="Overall agent status")
    details: SystemInfo = Field(..., description="Detailed system information")
    timestamp: Optional[str] = Field(None, description="Status check timestamp")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['healthy', 'degraded', 'error']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class CollectionStats(BaseModel):
    collection_name: str = Field(..., description="Collection name")
    total_documents: int = Field(..., ge=0, description="Total number of documents")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    index_status: Optional[str] = Field(None, description="Index status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class GetRAGStatsResponse(BaseModel):
    collection_stats: CollectionStats = Field(..., description="Collection statistics")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    error: Optional[str] = Field(None, description="Error message if any")


class GetTemplatesByTagsResponse(BaseModel):
    tags: List[str] = Field(..., description="Requested tags")
    templates: List[TemplateInfo] = Field(..., description="List of matching templates")
    total_results: int = Field(..., ge=0, description="Total number of results")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if not v:
            raise ValueError('At least one tag is required')
        return v


class ReloadTemplatesResponse(BaseModel):
    success: bool = Field(..., description="Whether reload was successful")
    templates_loaded: int = Field(..., ge=0, description="Number of templates loaded")
    message: str = Field(..., description="Status message")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        return v.strip()


class ClearRAGCollectionResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    collection_name: Optional[str] = Field(None, description="Collection name that was cleared")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if any")
    cleared_count: Optional[int] = Field(None, ge=0, description="Number of items cleared")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['success', 'failed', 'partial']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


# Common DTOs that are shared
class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NucleiInfo(BaseModel):
    name: str = Field(..., description="Template name")
    author: List[str] = Field(..., description="Template authors")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    description: str = Field(..., description="Vulnerability description")
    reference: Optional[List[str]] = Field(None, description="References")
    classification: Optional[Dict[str, Any]] = Field(None, description="Classification info")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Template tags")


class HttpRequest(BaseModel):
    method: TemplateMethod = Field(default=TemplateMethod.GET)
    path: List[str] = Field(..., description="Request paths")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    body: Optional[str] = Field(None, description="Request body")
    raw: Optional[List[str]] = Field(None, description="Raw HTTP requests")


class Matcher(BaseModel):
    type: str = Field(..., description="Matcher type (word, regex, status, etc.)")
    words: Optional[List[str]] = Field(None, description="Words to match")
    regex: Optional[List[str]] = Field(None, description="Regex patterns")
    status: Optional[List[int]] = Field(None, description="Status codes")
    condition: Optional[str] = Field(None, description="Matching condition")
    part: Optional[str] = Field(None, description="Part to match (body, header, etc.)")
    case_insensitive: Optional[bool] = Field(None, description="Case insensitive matching")


class Extractor(BaseModel):
    type: str = Field(..., description="Extractor type")
    regex: Optional[List[str]] = Field(None, description="Regex patterns")
    part: Optional[str] = Field(None, description="Part to extract from")
    group: Optional[int] = Field(None, description="Regex group")


class NucleiTemplate(BaseModel):
    id: str = Field(..., description="Template ID")
    info: NucleiInfo = Field(..., description="Template info")
    http: Optional[List[HttpRequest]] = Field(None, description="HTTP requests")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    matchers: Optional[List[Matcher]] = Field(None, description="Response matchers")
    extractors: Optional[List[Extractor]] = Field(None, description="Data extractors")
    matchers_condition: Optional[str] = Field(None, description="Matchers condition")


class TargetInfo(BaseModel):
    url: str = Field(..., description="Target URL", min_length=1, max_length=2000)
    method: TemplateMethod = Field(default=TemplateMethod.GET)
    parameters: Optional[List[str]] = Field(None, description="URL/form parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    cookies: Optional[Dict[str, str]] = Field(None, description="Cookies")

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


class TemplateGenerationRequest(BaseModel):
    vulnerability_description: str = Field(..., min_length=10, max_length=1000, description="Description of the vulnerability")
    target_info: TargetInfo = Field(..., description="Target information")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    author: Optional[str] = Field(None, description="Template author")
    references: Optional[List[str]] = Field(None, description="References")


class TemplateGenerationResponse(BaseModel):
    success: bool = Field(..., description="Generation success status")
    template_id: str = Field(..., description="Generated template ID")
    generated_template: str = Field(..., description="Generated YAML template")
    validation_result: ValidationResult = Field(..., description="Template validation result")
    retrieval_context: Optional[List[str]] = Field(None, description="Retrieved similar templates")
    generation_metadata: Dict[str, Any] = Field(default={}, description="Generation metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateValidationRequest(BaseModel):
    template_content: str = Field(..., min_length=10, max_length=50000, description="YAML template content")
    validate_syntax_only: bool = Field(default=False, description="Only validate YAML syntax")

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


class TemplateValidationResponse(BaseModel):
    validation_result: ValidationResult = Field(..., description="Validation result")
    template_id: Optional[str] = Field(None, description="Extracted template ID")
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")


class RAGSearchResponse(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    query: str = Field(..., description="Original query")
    total_results: int = Field(..., description="Total number of results")


class UpdateRAGDataRequest(BaseModel):
    vector_db: Optional[Dict[str, Any]] = Field(None, description="Vector DB configuration")
    llm: Optional[Dict[str, Any]] = Field(None, description="LLM configuration")
    nuclei: Optional[Dict[str, Any]] = Field(None, description="Nuclei configuration")
    rag: Optional[Dict[str, Any]] = Field(None, description="RAG configuration")
    force_update: bool = Field(default=False, description="Force update even if templates exist")


class UpdateRAGDataResponse(BaseModel):
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update result message")
    templates_cleared: int = Field(default=0, description="Number of templates cleared")
    templates_downloaded: int = Field(default=0, description="Number of templates downloaded")
    templates_loaded: int = Field(default=0, description="Number of templates loaded to database")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")