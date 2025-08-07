"""
AI Agent for generating Nuclei templates using LangChain and RAG
"""
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.rag_engine import RAGEngine
from app.core.nuclei_runner import NucleiRunner
from app.models.template import (
    TemplateGenerationRequest,
    TemplateGenerationResponse,
    ValidationResult
)


logger = logging.getLogger(__name__)


class NucleiAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_config()
        self.rag_engine = RAGEngine(self.config)
        self.nuclei_runner = NucleiRunner(self.config.get("nuclei", {}))
        self.llm = self._initialize_llm()
        self.model_name = self._get_model_name()
        self.system_prompt = self._load_system_prompt()
        self.user_prompt_template = self._load_user_prompt_template()
        
    def _load_config(self) -> Dict[str, Any]:
        config_path = Path("config/config.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _initialize_llm(self):
        llm_config = self.config.get("llm", {})
        provider = llm_config.get("provider", "openai")
        
        # Load API keys from secrets
        secrets_path = Path("config/secrets.yaml")
        secrets = {}
        if secrets_path.exists():
            with open(secrets_path, 'r') as f:
                secrets = yaml.safe_load(f)
        
        if provider == "gemini":
            api_key = secrets.get("gemini_api_key") or secrets.get("gemini", {}).get("api_key")
            return ChatGoogleGenerativeAI(
                model=llm_config.get("model", "gemini-2.0-flash"),
                temperature=llm_config.get("temperature", 0.7),
                max_tokens=llm_config.get("max_tokens", 2000),
                timeout=llm_config.get("timeout", 30),
                google_api_key=api_key
            )
        else:  # Default to OpenAI
            api_key = secrets.get("openai_api_key") or secrets.get("openai", {}).get("api_key")
            return ChatOpenAI(
                model=llm_config.get("model", "gpt-4"),
                temperature=llm_config.get("temperature", 0.7),
                max_tokens=llm_config.get("max_tokens", 2000),
                timeout=llm_config.get("timeout", 30),
                openai_api_key=api_key
            )
    
    def _load_system_prompt(self) -> str:
        prompt_path = Path("templates/nuclei_prompts/system_prompt.txt")
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        return "You are an expert Nuclei template generator."
    
    def _get_model_name(self) -> str:
        """Get the model name from configuration"""
        llm_config = self.config.get("llm", {})
        provider = llm_config.get("provider", "openai")
        if provider == "gemini":
            return llm_config.get("model", "gemini-2.0-flash-exp")
        else:
            return llm_config.get("model", "gpt-4")
    
    def _load_user_prompt_template(self) -> str:
        template_path = Path("templates/nuclei_prompts/user_prompt_template.txt")
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        return "Generate a Nuclei template for: {vulnerability_description}"
    
    async def generate_template(self, request: TemplateGenerationRequest) -> TemplateGenerationResponse:
        logger.info(f"Starting template generation for: {request.vulnerability_description[:100]}...")
        
        try:
            # Initialize RAG engine if needed
            if not self.rag_engine.initialized:
                await self.rag_engine.initialize()
            
            # Retrieve similar templates for context
            similar_templates = await self.rag_engine.retrieve_similar_templates(
                query=request.vulnerability_description,
                max_results=5
            )
            
            # Format retrieval context
            retrieval_context = self.rag_engine.format_retrieval_context(similar_templates)
            
            # Generate template with retries
            max_retries = self.config.get("template_generation", {}).get("max_retries", 3)
            generated_template = None
            validation_result = None
            
            for attempt in range(max_retries):
                try:
                    generated_template = await self._generate_template_content(request, retrieval_context)
                    
                    # Validate the generated template
                    if self.config.get("template_generation", {}).get("validation_required", True):
                        validation_result = await self.nuclei_runner.validate_template(generated_template)
                        
                        if validation_result.is_valid:
                            break
                        else:
                            logger.warning(f"Generated template failed validation (attempt {attempt + 1}): {validation_result.errors}")
                            if attempt < max_retries - 1:
                                # Try to improve the template based on validation errors
                                generated_template = await self._refine_template(
                                    generated_template, 
                                    validation_result, 
                                    request
                                )
                    else:
                        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
                        break
                        
                except Exception as e:
                    logger.error(f"Template generation attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
            
            if not generated_template:
                raise Exception("Failed to generate valid template after all retries")
            
            # Extract template ID
            template_id = self._extract_template_id(generated_template)
            
            # Create response
            response = TemplateGenerationResponse(
                success=True,
                template_id=template_id,
                generated_template=generated_template,
                validation_result=validation_result,
                retrieval_context=[doc.get("content", "")[:200] + "..." for doc in similar_templates[:3]],
                generation_metadata={
                    "model": self.model_name,
                    "similar_templates_count": len(similar_templates),
                    "generation_attempts": attempt + 1,
                    "request_severity": request.severity,
                    "target_method": request.target_info.method
                }
            )
            
            logger.info(f"Template generation completed successfully: {template_id}")
            return response
            
        except Exception as e:
            logger.error(f"Template generation failed: {e}")
            return TemplateGenerationResponse(
                success=False,
                template_id="failed_generation",
                generated_template="",
                validation_result=ValidationResult(
                    is_valid=False,
                    errors=[f"Generation failed: {str(e)}"],
                    warnings=[]
                ),
                generation_metadata={"error": str(e)}
            )
    
    async def _generate_template_content(
        self, 
        request: TemplateGenerationRequest, 
        retrieval_context: str
    ) -> str:
        # Format user prompt
        user_prompt = self.user_prompt_template.format(
            vulnerability_description=request.vulnerability_description,
            severity=request.severity,
            target_url=request.target_info.url,
            http_method=request.target_info.method,
            parameters=", ".join(request.target_info.parameters or []),
            additional_context=f"Tags: {', '.join(request.tags or [])}\nAuthor: {request.author or 'AI Agent'}\nReferences: {', '.join(request.references or [])}",
            retrieval_context=retrieval_context
        )
        
        # Create messages
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Generate template
        response = await self.llm.agenerate([messages])
        generated_content = response.generations[0][0].text.strip()
        
        # Extract YAML from response (in case it's wrapped in markdown)
        yaml_content = self._extract_yaml_content(generated_content)
        
        return yaml_content
    
    def _extract_yaml_content(self, content: str) -> str:
        lines = content.split('\n')
        yaml_lines = []
        in_yaml_block = False
        
        for line in lines:
            if line.strip().startswith('```yaml') or line.strip().startswith('```yml'):
                in_yaml_block = True
                continue
            elif line.strip() == '```' and in_yaml_block:
                break
            elif in_yaml_block or (not any(line.strip().startswith(prefix) for prefix in ['```', '#', '**', '*'])):
                yaml_lines.append(line)
        
        yaml_content = '\n'.join(yaml_lines).strip()
        
        # If no YAML block found, use the entire content
        if not yaml_content:
            yaml_content = content
        
        return yaml_content
    
    def _extract_template_id(self, template_content: str) -> str:
        try:
            template_data = yaml.safe_load(template_content)
            return template_data.get("id", f"generated_{uuid.uuid4().hex[:8]}")
        except:
            return f"generated_{uuid.uuid4().hex[:8]}"
    
    async def _refine_template(
        self, 
        template_content: str, 
        validation_result: ValidationResult, 
        original_request: TemplateGenerationRequest
    ) -> str:
        refinement_prompt = f"""
The generated Nuclei template has validation errors. Please fix the following issues:

Validation Errors:
{chr(10).join(validation_result.errors)}

Validation Warnings:
{chr(10).join(validation_result.warnings)}

Original Template:
```yaml
{template_content}
```

Please provide a corrected version of the template that addresses these validation issues while maintaining the original functionality for detecting: {original_request.vulnerability_description}
"""
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=refinement_prompt)
        ]
        
        response = await self.llm.agenerate([messages])
        refined_content = response.generations[0][0].text.strip()
        
        return self._extract_yaml_content(refined_content)
    
    async def validate_template_content(self, template_content: str) -> ValidationResult:
        return await self.nuclei_runner.validate_template(template_content)
    
    async def get_agent_status(self) -> Dict[str, Any]:
        nuclei_available = await self.nuclei_runner.check_nuclei_available()
        nuclei_version = await self.nuclei_runner.get_nuclei_version()
        rag_stats = await self.rag_engine.get_collection_stats()
        
        return {
            "nuclei_available": nuclei_available,
            "nuclei_version": nuclei_version,
            "rag_engine_initialized": self.rag_engine.initialized,
            "rag_collection_stats": rag_stats,
            "llm_model": self.model_name,
            "config_loaded": bool(self.config)
        }