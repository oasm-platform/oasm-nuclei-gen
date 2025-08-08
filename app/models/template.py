"""
Pydantic models for Nuclei templates and API requests/responses
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator


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
    url: str = Field(..., description="Target URL")
    method: TemplateMethod = Field(default=TemplateMethod.GET)
    parameters: Optional[List[str]] = Field(None, description="URL/form parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    cookies: Optional[Dict[str, str]] = Field(None, description="Cookies")


class TemplateGenerationRequest(BaseModel):
    vulnerability_description: str = Field(..., min_length=10, max_length=1000, description="Description of the vulnerability")
    target_info: TargetInfo = Field(..., description="Target information")
    severity: SeverityLevel = Field(..., description="Vulnerability severity")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    author: Optional[str] = Field(None, description="Template author")
    references: Optional[List[str]] = Field(None, description="References")


class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")


class TemplateGenerationResponse(BaseModel):
    success: bool = Field(..., description="Generation success status")
    template_id: str = Field(..., description="Generated template ID")
    generated_template: str = Field(..., description="Generated YAML template")
    validation_result: ValidationResult = Field(..., description="Template validation result")
    retrieval_context: Optional[List[str]] = Field(None, description="Retrieved similar templates")
    generation_metadata: Dict[str, Any] = Field(default={}, description="Generation metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateValidationRequest(BaseModel):
    template_content: str = Field(..., description="YAML template content")
    validate_syntax_only: bool = Field(default=False, description="Only validate YAML syntax")


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



class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)