"""
API v1 endpoints for Nuclei template generation using LLM + RAG
Simplified version without complex agent pattern
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Request

from app.core.nuclei_service import NucleiTemplateService
from app.api.v1.v1_dto import (
    TemplateGenerationRequest,
    TemplateGenerationResponse,
    ErrorResponse,
    ReloadTemplatesResponse,
    ClearRAGCollectionResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def get_nuclei_service(request: Request) -> NucleiTemplateService:
    """Get or create NucleiTemplateService instance"""
    if not hasattr(request.app.state, 'nuclei_service'):
        request.app.state.nuclei_service = NucleiTemplateService()
    return request.app.state.nuclei_service

@router.post("/generate_template", response_model=TemplateGenerationResponse)
async def generate_template(
    request_data: TemplateGenerationRequest,
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> TemplateGenerationResponse:
    """
    Generate a new Nuclei security template using LLM + RAG from a simple text prompt.
    """
    try:        
        response = await service.generate_template(request_data)
        return response
        
    except Exception as e:
        logger.error(f"Error in generate_template endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template generation",
                details={"exception": str(e)}
            ).model_dump()
        )

@router.put("/reload_templates")
async def reload_templates(
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> ReloadTemplatesResponse:
    """
    Reload all Nuclei templates into the RAG collection.
    """
    try:        
        count = await service.rag_engine.reload_templates()
        
        return ReloadTemplatesResponse(
            success=True,
            templates_loaded=count,
            message=f"Successfully reloaded {count} templates"
        )
        
    except Exception as e:
        logger.error(f"Error reloading templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template reload",
                details={"exception": str(e)}
            ).model_dump()
        )



@router.delete("/rag_collection")
async def clear_rag_collection(
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> ClearRAGCollectionResponse:
    """
    Clear all templates and embeddings from the RAG collection.
    """
    try:        
        if not service.rag_engine.initialized:
            await service.rag_engine.initialize()
        
        result = await service.rag_engine.vector_db.clear_collection()
        
        return ClearRAGCollectionResponse(
            status=result.get("status", "unknown"),
            collection_name=result.get("collection_name"),
            message=result.get("message"),
            error=result.get("error"),
            cleared_count=result.get("cleared_count")
        )
        
    except Exception as e:
        logger.error(f"Error clearing collection: {e}")
        return ClearRAGCollectionResponse(
            status="failed",
            error=f"Internal server error during collection clear: {str(e)}"
        )