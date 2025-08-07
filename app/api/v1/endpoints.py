"""
API v1 endpoints for Nuclei template generation and validation
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from app.core.agent import NucleiAgent
from app.models.template import (
    TemplateGenerationRequest,
    TemplateGenerationResponse,
    TemplateValidationRequest,
    TemplateValidationResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    ErrorResponse
)


logger = logging.getLogger(__name__)
router = APIRouter()


def get_nuclei_agent(request: Request) -> NucleiAgent:
    if not hasattr(request.app.state, 'nuclei_agent'):
        request.app.state.nuclei_agent = NucleiAgent()
    return request.app.state.nuclei_agent


@router.post("/generate_template", response_model=TemplateGenerationResponse)
async def generate_template(
    request_data: TemplateGenerationRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> TemplateGenerationResponse:
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
            ).dict()
        )


@router.post("/validate_template", response_model=TemplateValidationResponse)
async def validate_template(
    request_data: TemplateValidationRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> TemplateValidationResponse:
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
            ).dict()
        )


@router.post("/search_templates", response_model=RAGSearchResponse)
async def search_templates(
    request_data: RAGSearchRequest,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> RAGSearchResponse:
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
            ).dict()
        )


@router.get("/agent_status")
async def get_agent_status(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    try:
        status = await agent.get_agent_status()
        return {
            "status": "healthy" if status["nuclei_available"] else "degraded",
            "details": status
        }
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/rag_stats")
async def get_rag_stats(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        stats = await agent.rag_engine.get_collection_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return {
            "error": str(e)
        }


@router.post("/reload_templates")
async def reload_templates(
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    try:
        logger.info("Template reload request received")
        
        count = await agent.rag_engine.reload_templates()
        
        return {
            "success": True,
            "templates_loaded": count,
            "message": f"Successfully reloaded {count} templates"
        }
        
    except Exception as e:
        logger.error(f"Error reloading templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template reload",
                details={"exception": str(e)}
            ).dict()
        )


@router.get("/templates/severity/{severity}")
async def get_templates_by_severity(
    severity: str,
    max_results: int = 10,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        templates = await agent.rag_engine.get_templates_by_severity(
            severity=severity,
            max_results=max_results
        )
        
        return {
            "severity": severity,
            "templates": templates,
            "total_results": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Error getting templates by severity: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e)}
            ).dict()
        )


@router.post("/templates/tags")
async def get_templates_by_tags(
    tags: list[str],
    max_results: int = 10,
    agent: NucleiAgent = Depends(get_nuclei_agent)
) -> Dict[str, Any]:
    try:
        if not agent.rag_engine.initialized:
            await agent.rag_engine.initialize()
        
        templates = await agent.rag_engine.get_templates_by_tags(
            tags=tags,
            max_results=max_results
        )
        
        return {
            "tags": tags,
            "templates": templates,
            "total_results": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Error getting templates by tags: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error during template search",
                details={"exception": str(e)}
            ).model_dump()
        )