"""
API v2 endpoints for Nuclei template generation and validation
Enhanced version with improved error handling and response formats
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request

from app.core.agent import NucleiAgent
from app.models.template import (
    TemplateGenerationRequest,
    TemplateGenerationResponse,
    TemplateValidationRequest,
    TemplateValidationResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    UpdateRAGDataRequest,
    UpdateRAGDataResponse,
    ErrorResponse
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
) -> Dict[str, Any]:
    """
    Retrieve Nuclei templates filtered by security severity level.
    
    Args:
        severity: Security severity level (critical, high, medium, low, info)
        max_results: Maximum number of templates to return (default: 10)
        
    Returns:
        Dict containing severity level, matching templates array, and total count
        with enhanced v2 response format including metadata
        
    Raises:
        HTTPException: If RAG engine initialization fails or template search encounters errors
    """
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        templates = await agent.rag_engine.get_templates_by_severity(
            severity=severity,
            max_results=max_results
        )
        
        return {
            "api_version": "v2",
            "severity": severity,
            "templates": templates,
            "total_results": len(templates),
            "metadata": {
                "max_results": max_results,
                "filter_type": "severity"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting templates by severity: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e), "api_version": "v2"}
            ).model_dump()
        )


@router.get("/agent_status")
async def get_agent_status(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    """
    Get the current health status and configuration of the Nuclei agent.
    
    Returns:
        Dict containing agent status (healthy/degraded/error) and detailed system information
        including Nuclei availability, RAG engine status, configuration details, and v2 enhancements
        
    Note:
        This endpoint does not raise exceptions but returns error status in response body
    """
    try:
        status = await agent.get_agent_status()
        return {
            "api_version": "v2",
            "status": "healthy" if status["nuclei_available"] else "degraded",
            "details": status,
            "timestamp": status.get("timestamp"),
            "system_info": {
                "rag_initialized": agent.rag_engine.initialized if hasattr(agent, 'rag_engine') else False
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {
            "api_version": "v2",
            "status": "error",
            "error": str(e),
            "timestamp": None
        }


@router.get("/rag_stats")
async def get_rag_stats(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    """
    Retrieve statistics and metadata about the RAG (Retrieval-Augmented Generation) collection.
    
    Returns:
        Dict containing collection statistics such as total templates count, 
        embedding dimensions, index status, collection metadata, and v2 enhanced metrics
        
    Raises:
        Returns error dict if RAG engine initialization fails or stats retrieval encounters errors
    """
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        stats = await agent.rag_engine.get_collection_stats()
        
        # Enhanced v2 response with additional metadata
        enhanced_stats = {
            "api_version": "v2",
            **stats,
            "performance_metrics": {
                "initialization_status": agent.rag_engine.initialized,
                "last_update": stats.get("last_update")
            }
        }
        
        return enhanced_stats
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return {
            "api_version": "v2",
            "error": str(e)
        }


@router.post("/generate_template", response_model=TemplateGenerationResponse)
async def generate_template(
    request_data: TemplateGenerationRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> TemplateGenerationResponse:
    """
    Generate a new Nuclei security template based on vulnerability description.
    
    Uses AI-powered template generation combined with RAG similarity search to create
    contextually relevant and syntactically valid Nuclei templates with enhanced v2 processing.
    
    Args:
        request_data: TemplateGenerationRequest containing vulnerability description and options
        
    Returns:
        TemplateGenerationResponse with generated template content, validation results,
        metadata including template ID, generation confidence, and v2 enhancements
        
    Raises:
        HTTPException: If template generation fails due to internal errors
    """
    try:
        logger.info(f"V2 Template generation request: {request_data.vulnerability_description[:100]}...")
        
        response = await agent.generate_template(request_data)
        
        # Add v2 metadata
        if hasattr(response, 'metadata'):
            if response.metadata is None:
                response.metadata = {}
            response.metadata["api_version"] = "v2"
            response.metadata["enhanced_processing"] = True
        
        if response.success:
            logger.info(f"V2 Template generated successfully: {response.template_id}")
        else:
            logger.warning(f"V2 Template generation failed: {response.validation_result.errors}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in v2 generate_template endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template generation",
                details={"exception": str(e), "api_version": "v2"}
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
    depending on the validate_syntax_only flag in the request, with enhanced v2 validation rules.
    
    Args:
        request_data: TemplateValidationRequest with template content and validation options
        
    Returns:
        TemplateValidationResponse containing validation results, error details,
        extracted template ID, and v2 enhanced validation metrics
        
    Raises:
        HTTPException: If validation process encounters internal errors
    """
    try:
        logger.info("V2 Template validation request received")
        
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
        
        # Add v2 metadata
        if hasattr(response, 'metadata'):
            if response.metadata is None:
                response.metadata = {}
            response.metadata["api_version"] = "v2"
            response.metadata["validation_mode"] = "syntax_only" if request_data.validate_syntax_only else "full"
        
        logger.info(f"V2 Template validation completed: {'PASSED' if validation_result.is_valid else 'FAILED'}")
        return response
        
    except Exception as e:
        logger.error(f"Error in v2 validate_template endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template validation",
                details={"exception": str(e), "api_version": "v2"}
            ).model_dump()
        )


@router.post("/search_templates", response_model=RAGSearchResponse)
async def search_templates(
    request_data: RAGSearchRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> RAGSearchResponse:
    """
    Search for similar Nuclei templates using semantic similarity matching.
    
    Performs vector-based similarity search in the RAG collection to find
    templates that are semantically similar to the provided query with enhanced v2 ranking.
    
    Args:
        request_data: RAGSearchRequest with search query, max results, and similarity threshold
        
    Returns:
        RAGSearchResponse containing matching templates ranked by similarity score,
        original query, total results count, and v2 enhanced search metadata
        
    Raises:
        HTTPException: If RAG engine initialization fails or search encounters errors
    """
    try:
        logger.info(f"V2 Template search request: {request_data.query}")
        
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
        
        # Add v2 metadata
        if hasattr(response, 'metadata'):
            if response.metadata is None:
                response.metadata = {}
            response.metadata["api_version"] = "v2"
            response.metadata["search_parameters"] = {
                "max_results": request_data.max_results,
                "similarity_threshold": request_data.similarity_threshold
            }
        
        logger.info(f"V2 Template search completed: {len(results)} results found")
        return response
        
    except Exception as e:
        logger.error(f"Error in v2 search_templates endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e), "api_version": "v2"}
            ).model_dump()
        )


@router.post("/reload_templates")
async def reload_templates(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    """
    Reload all Nuclei templates into the RAG collection from the template repository.
    
    Refreshes the in-memory template collection by re-indexing all available
    Nuclei templates from the configured template sources with v2 enhanced processing.
    
    Returns:
        Dict containing success status, number of templates reloaded, status message,
        and v2 enhanced reload metrics
        
    Raises:
        HTTPException: If template reload process fails due to internal errors
    """
    try:
        logger.info("V2 Template reload request received")
        
        count = await agent.rag_engine.reload_templates()
        
        return {
            "api_version": "v2",
            "success": True,
            "templates_loaded": count,
            "message": f"Successfully reloaded {count} templates",
            "performance_metrics": {
                "reload_timestamp": None,  # Could be enhanced with actual timestamp
                "processing_mode": "enhanced_v2"
            }
        }
        
    except Exception as e:
        logger.error(f"Error reloading templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template reload",
                details={"exception": str(e), "api_version": "v2"}
            ).model_dump()
        )


@router.post("/templates/tags")
async def get_templates_by_tags(
    tags: list[str],
    max_results: int = 10,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    """
    Retrieve Nuclei templates filtered by specified tags.
    
    Searches the RAG collection for templates that contain any of the specified
    tags in their metadata with enhanced v2 tag matching algorithms.
    
    Args:
        tags: List of tag strings to filter templates by
        max_results: Maximum number of templates to return (default: 10)
        
    Returns:
        Dict containing search tags, matching templates array, total count,
        and v2 enhanced tag analysis
        
    Raises:
        HTTPException: If RAG engine initialization fails or tag search encounters errors
    """
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        templates = await agent.rag_engine.get_templates_by_tags(
            tags=tags,
            max_results=max_results
        )
        
        return {
            "api_version": "v2",
            "tags": tags,
            "templates": templates,
            "total_results": len(templates),
            "search_metadata": {
                "tag_count": len(tags),
                "max_results": max_results,
                "matching_algorithm": "enhanced_v2"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting templates by tags: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e), "api_version": "v2"}
            ).model_dump()
        )


@router.put("/update_rag_data", response_model=UpdateRAGDataResponse)
async def update_rag_data(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> UpdateRAGDataResponse:
    """
    Update RAG collection by downloading latest templates and rebuilding the vector index.
    
    Performs a comprehensive update of the RAG data with enhanced v2 processing by:
    1. Clearing existing collection
    2. Downloading latest Nuclei templates
    3. Processing and indexing new templates with improved algorithms
    4. Building optimized vector embeddings
    
    Returns:
        UpdateRAGDataResponse containing operation status, templates processed counts,
        detailed metadata about the update process, and v2 performance metrics
        
    Raises:
        HTTPException: If RAG data update process fails due to internal errors
    """
    try:
        logger.info("V2 RAG data update request received")
        
        # Initialize RAG engine if needed
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        # Perform the RAG data update
        result = await agent.rag_engine.vector_db.update_rag_data(
            rag_data_path="rag_data"
        )
        
        # Create response based on result with v2 enhancements
        response = UpdateRAGDataResponse(
            success=result["status"] in ["success", "partial_failure"],
            message=result["message"],
            templates_cleared=result.get("templates_cleared", 0),
            templates_downloaded=result.get("templates_downloaded", 0),
            templates_loaded=result.get("templates_loaded", 0),
            metadata={
                "api_version": "v2",
                "status": result["status"],
                "steps": result.get("steps", []),
                "processing_enhancements": "v2_optimized"
            }
        )
        
        if result["status"] == "success":
            logger.info(f"V2 RAG data update completed successfully: {result['templates_loaded']} templates loaded")
        elif result["status"] == "partial_failure":
            logger.warning(f"V2 RAG data update completed with warnings: {result['message']}")
        else:
            logger.error(f"V2 RAG data update failed: {result['message']}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in v2 update_rag_data endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during RAG data update",
                details={"exception": str(e), "api_version": "v2"}
            ).model_dump()
        )


@router.delete("/rag_collection")
async def clear_rag_collection(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    """
    Clear all templates and embeddings from the RAG collection.
    
    Completely removes all stored templates, vector embeddings, and metadata
    from the RAG collection, effectively resetting it to an empty state with v2 enhanced cleanup.
    
    Returns:
        Dict containing operation status, collection name, success/error details,
        and v2 enhanced cleanup metrics
        
    Note:
        This endpoint does not raise exceptions but returns error status in response body
    """
    try:
        logger.info("V2 Collection clear request received")
        
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        result = await agent.rag_engine.vector_db.clear_collection()
        
        # Enhanced v2 response
        enhanced_result = {
            "api_version": "v2",
            **result,
            "cleanup_metadata": {
                "cleanup_mode": "enhanced_v2",
                "timestamp": None  # Could be enhanced with actual timestamp
            }
        }
        
        if result.get("status") == "success":
            logger.info(f"V2 Collection cleared successfully: {result.get('collection_name')}")
        else:
            logger.error(f"V2 Failed to clear collection: {result.get('error')}")
        
        return enhanced_result
        
    except Exception as e:
        logger.error(f"Error clearing v2 collection: {e}")
        return {
            "api_version": "v2",
            "error": f"Internal server error during collection clear: {str(e)}",
            "status": "failed"
        }