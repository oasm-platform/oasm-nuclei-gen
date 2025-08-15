"""
DTOs for API v1 endpoints
Contains Pydantic models for all API v1 endpoints including validation schemas
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


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

class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class TemplateGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=2000, description="Text prompt describing the vulnerability or security test")


class TemplateGenerationResponse(BaseModel):
    success: bool = Field(..., description="Generation success status")
    template_id: str = Field(..., description="Generated template ID")
    generated_template: str = Field(..., description="Generated YAML template")
    created_at: datetime = Field(default_factory=datetime.utcnow)
