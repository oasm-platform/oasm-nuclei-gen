"""
Common models and DTOs for the core application
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Model for template validation results"""
    is_valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")


class TemplateGenerationRequest(BaseModel):
    """Request model for template generation"""
    prompt: str = Field(..., min_length=10, max_length=2000, description="Text prompt describing the vulnerability or security test")


class TemplateGenerationResponse(BaseModel):
    """Response model for template generation"""
    success: bool = Field(..., description="Generation success status")
    template_id: str = Field(..., description="Generated template ID")
    generated_template: str = Field(..., description="Generated YAML template")
    created_at: datetime = Field(default_factory=datetime.utcnow)