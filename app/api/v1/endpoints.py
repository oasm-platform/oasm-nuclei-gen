"""
API v1 endpoints for Nuclei template generation and validation
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Request

from app.core.agent import NucleiAgent
from app.api.v1.v1_dto import (
    GetRagStats,
    GetTemplatesBySeverityResponse,
    TemplateGenerationRequest,
    TemplateGenerationResponse,
    TemplateValidationRequest,
    TemplateValidationResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    ErrorResponse,
    GetTemplatesByTagsResponse,
    ReloadTemplatesResponse,
    ClearRAGCollectionResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def get_nuclei_agent(request: Request) -> NucleiAgent:
    if not hasattr(request.app.state, 'nuclei_agent'):
        request.app.state.nuclei_agent = NucleiAgent()
    return request.app.state.nuclei_agent


@router.get("/templates/severity/{severity}")
async def get_templates_by_severity(
    severity: str,
    max_results: int = 10,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> GetTemplatesBySeverityResponse:
    """
    Retrieve Nuclei templates filtered by security severity level.
    """
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        templates = await agent.rag_engine.get_templates_by_severity(
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

@router.get("/templates/tags")
async def get_templates_by_tags(
    tags: list[str],
    max_results: int = 10,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> GetTemplatesByTagsResponse:
    """
    Retrieve Nuclei templates filtered by specified tags.
    
    Searches the RAG collection for templates that contain any of the specified
    tags in their metadata.
    """
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        templates = await agent.rag_engine.get_templates_by_tags(
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

@router.get("/search_templates", response_model=RAGSearchResponse)
async def search_templates(
    request_data: RAGSearchRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> RAGSearchResponse:
    """
    Search for similar Nuclei templates using semantic similarity matching.
    
    Performs vector-based similarity search in the RAG collection to find
    templates that are semantically similar to the provided query.
    """
    try:
        logger.info(f"Template search request: {request_data.query}")
        
        # Initialize RAG engine if needed
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        # Search for similar templates
        results = await agent.rag_engine.retrieve_similar_templates(
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



@router.get("/rag_stats")
async def get_rag_stats(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> GetRagStats:
    """
    Retrieve statistics and metadata about the RAG (Retrieval-Augmented Generation) collection.
    """
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        stats = await agent.rag_engine.get_collection_stats()
        return GetRagStats(
            total_documents=stats.get("total_documents", 0),
            collection_name=stats.get("collection_name", "")
        )
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during RAG stats retrieval",
                details={"exception": str(e)}
            ).model_dump()
        )



@router.post("/generate_template", response_model=TemplateGenerationResponse)
async def generate_template(
    request_data: TemplateGenerationRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> TemplateGenerationResponse:
    """
    Generate a new Nuclei security template based on vulnerability description.
    
    Uses AI-powered template generation combined with RAG similarity search to create
    contextually relevant and syntactically valid Nuclei templates.
    """
    try:
        logger.info(f"Template generation request: {request_data.vulnerability_description[:100]}...")
        
        response = await agent.generate_template(request_data)
        
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


@router.post("/validate_template", response_model=TemplateValidationResponse)
async def validate_template(
    request_data: TemplateValidationRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> TemplateValidationResponse:
    """
    Validate Nuclei template content for syntax correctness and compliance.
    
    Supports both YAML syntax validation and full Nuclei template validation
    depending on the validate_syntax_only flag in the request.
    """
    try:
        logger.info("Template validation request received")
        
        if request_data.validate_syntax_only:
            # Only validate YAML syntax
            validation_result = await agent.nuclei_runner.validate_yaml_syntax(
                request_data.template_content
            )
        else:
            # Full Nuclei validation
            validation_result = await agent.validate_template_content(
                request_data.template_content
            )
        
        # Try to extract template ID
        template_id = None
        try:
            import yaml
            template_data = yaml.safe_load(request_data.template_content)
            template_id = template_data.get("id")
        except:
            pass
        
        response = TemplateValidationResponse(
            validation_result=validation_result,
            template_id=template_id
        )
        
        logger.info(f"Template validation completed: {'PASSED' if validation_result.is_valid else 'FAILED'}")
        return response
        
    except Exception as e:
        logger.error(f"Error in validate_template endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template validation",
                details={"exception": str(e)}
            ).model_dump()
        )





@router.post("/reload_templates")
async def reload_templates(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> ReloadTemplatesResponse:
    """
    Reload all Nuclei templates into the RAG collection from the template repository.
    
    Refreshes the in-memory template collection by re-indexing all available
    Nuclei templates from the configured template sources.
    """
    try:
        logger.info("Template reload request received")
        
        count = await agent.rag_engine.reload_templates()
        
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
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> ClearRAGCollectionResponse:
    """
    Clear all templates and embeddings from the RAG collection.
    
    Completely removes all stored templates, vector embeddings, and metadata
    from the RAG collection, effectively resetting it to an empty state.
    """
    try:
        logger.info("Collection clear request received")
        
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        result = await agent.rag_engine.vector_db.clear_collection()
        
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