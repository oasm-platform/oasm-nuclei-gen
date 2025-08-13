"""
API v1 endpoints for Nuclei template generation using LLM + RAG
Simplified version without complex agent pattern
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request

from app.core.nuclei_service import NucleiTemplateService
from app.api.v1.v1_dto import (
    TemplateGenerationRequest,
    TemplateGenerationResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    UpdateRAGDataRequest,
    UpdateRAGDataResponse,
    ErrorResponse,
    GetTemplatesBySeverityResponse,
    GetAgentStatusResponse,
    GetRAGStatsResponse,
    GetTemplatesByTagsResponse,
    ReloadTemplatesResponse,
    ClearRAGCollectionResponse,
    SystemInfo
)


logger = logging.getLogger(__name__)
router = APIRouter()


def get_nuclei_service(request: Request) -> NucleiTemplateService:
    """Get or create NucleiTemplateService instance"""
    if not hasattr(request.app.state, 'nuclei_service'):
        request.app.state.nuclei_service = NucleiTemplateService()
    return request.app.state.nuclei_service


@router.get("/templates/severity/{severity}")
async def get_templates_by_severity(
    severity: str,
    max_results: int = 10,
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> GetTemplatesBySeverityResponse:
    """
    Retrieve Nuclei templates filtered by security severity level.
    """
    try:
        if not service.rag_engine.initialized:
            await service.rag_engine.initialize()
        
        templates = await service.rag_engine.get_templates_by_severity(
            severity=severity,
            max_results=max_results
        )
        
        return GetTemplatesBySeverityResponse(
            severity=severity,
            templates=templates,
            total_results=len(templates)
        )
        
    except Exception as e:
        logger.error(f"Error getting templates by severity: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e)}
            ).model_dump()
        )



@router.post("/generate_template", response_model=TemplateGenerationResponse)
async def generate_template(
    request_data: TemplateGenerationRequest,
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> TemplateGenerationResponse:
    """
    Generate a new Nuclei security template using LLM + RAG from a simple text prompt.
    """
    try:
        logger.info(f"Template generation request: {request_data.prompt[:100]}...")
        
        response = await service.generate_template(request_data)
        
        if response.success:
            logger.info(f"Template generated successfully: {response.template_id}")
        else:
            logger.warning(f"Template generation failed: {response.validation_result.errors}")
        
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




@router.post("/search_templates", response_model=RAGSearchResponse)
async def search_templates(
    request_data: RAGSearchRequest,
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> RAGSearchResponse:
    """
    Search for similar Nuclei templates using semantic similarity matching.
    """
    try:
        logger.info(f"Template search request: {request_data.query}")
        
        # Search for similar templates
        results = await service.search_templates(
            query=request_data.query,
            max_results=request_data.max_results,
            similarity_threshold=request_data.similarity_threshold
        )
        
        response = RAGSearchResponse(
            results=results,
            query=request_data.query,
            total_results=len(results)
        )
        
        logger.info(f"Template search completed: {len(results)} results found")
        return response
        
    except Exception as e:
        logger.error(f"Error in search_templates endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e)}
            ).model_dump()
        )




@router.post("/templates/tags")
async def get_templates_by_tags(
    tags: list[str],
    max_results: int = 10,
    service: NucleiTemplateService = Depends(get_nuclei_service)
) -> GetTemplatesByTagsResponse:
    """
    Retrieve Nuclei templates filtered by specified tags.
    """
    try:
        if not service.rag_engine.initialized:
            await service.rag_engine.initialize()
        
        templates = await service.rag_engine.get_templates_by_tags(
            tags=tags,
            max_results=max_results
        )
        
        return GetTemplatesByTagsResponse(
            tags=tags,
            templates=templates,
            total_results=len(templates)
        )
        
    except Exception as e:
        logger.error(f"Error getting templates by tags: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
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
        logger.info("Template reload request received")
        
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
        logger.info("Collection clear request received")
        
        if not service.rag_engine.initialized:
            await service.rag_engine.initialize()
        
        result = await service.rag_engine.vector_db.clear_collection()
        
        if result.get("status") == "success":
            logger.info(f"Collection cleared successfully: {result.get('collection_name')}")
        else:
            logger.error(f"Failed to clear collection: {result.get('error')}")
        
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