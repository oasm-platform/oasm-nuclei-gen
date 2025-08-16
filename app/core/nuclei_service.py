"""
Nuclei Template Service - Simplified service using LLM + RAG directly
This replaces the complex pattern with a simpler approach
"""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import yaml
import tempfile

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config_service import ConfigService
from app.core.rag_engine import RAGEngine
from app.core.nuclei_runner import NucleiRunner
from app.core.models import ValidationResult, TemplateGenerationRequest, TemplateGenerationResponse


logger = logging.getLogger(__name__)


class NucleiTemplateService:
    """Simple service that directly uses LLM + RAG for template generation"""
    
    def __init__(self):
        self.settings = ConfigService.get_settings()
        self.rag_engine = RAGEngine()
        self.nuclei_runner = NucleiRunner()
        self.llm = self._initialize_llm()
        self.model_name = self._get_model_name()
        self.system_prompt = self._load_system_prompt()
        self.user_prompt_template = self._load_user_prompt_template()
        
    def _initialize_llm(self):
        """Initialize LLM from environment variables"""
        provider = self.settings.llm.provider
        
        logger.info(f"Initializing LLM with provider: {provider}")
        
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is required for Gemini provider")
            
            return ChatGoogleGenerativeAI(
                model=self.settings.llm.model,
                temperature=self.settings.llm.temperature,
                max_tokens=self.settings.llm.max_tokens,
                timeout=self.settings.llm.timeout,
                google_api_key=api_key
            )
        else:  # OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
            
            return ChatOpenAI(
                model=self.settings.llm.model,
                temperature=self.settings.llm.temperature,
                max_tokens=self.settings.llm.max_tokens,
                timeout=self.settings.llm.timeout,
                openai_api_key=api_key
            )
    
    def _get_model_name(self) -> str:
        """Get the model name from configuration"""
        return self.settings.llm.model
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file or use default"""
        prompt_path = Path("templates/nuclei_prompts/system_prompt.txt")
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        return "You are an expert Nuclei template generator. Generate valid YAML templates for security testing."
    
    def _load_user_prompt_template(self) -> str:
        """Load user prompt template from file or use default"""
        template_path = Path("templates/nuclei_prompts/user_prompt_template.txt")
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        return """Generate a Nuclei template based on the following request:

{prompt}

Similar templates for reference:
{retrieval_context}

Please generate a complete, valid YAML Nuclei template that tests for the described vulnerability or security issue."""

    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        nuclei_available = await self.nuclei_runner.check_nuclei_available()
        nuclei_version = await self.nuclei_runner.get_nuclei_version()
        rag_stats = await self.rag_engine.get_collection_stats()
        
        return {
            "nuclei_available": nuclei_available,
            "nuclei_version": nuclei_version,
            "rag_engine_initialized": self.rag_engine.initialized,
            "rag_collection_stats": rag_stats,
            "llm_model": self.model_name,
            "config_loaded": bool(self.settings)
        }

    async def search_templates(
        self, 
        query: str, 
        max_results: int = 5, 
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar templates using RAG"""
        if not self.rag_engine.initialized:
            await self.rag_engine.initialize()
        
        return await self.rag_engine.retrieve_similar_templates(
            query=query,
            max_results=max_results,
            similarity_threshold=similarity_threshold
        )

    async def validate_template(self, template_content: str) -> ValidationResult:
        """Validate a template using Nuclei runner"""
        return await self.nuclei_runner.validate_template(template_content)
    
    async def generate_template(self, request: TemplateGenerationRequest) -> TemplateGenerationResponse:
        """Generate a Nuclei template using LLM + RAG"""        
        try:
            # Initialize RAG engine if needed
            if not self.rag_engine.initialized:
                await self.rag_engine.initialize()
            
            # Retrieve similar templates for context
            similar_templates = await self.rag_engine.retrieve_similar_templates(
                query=request.prompt,
                max_results=self.settings.rag.max_retrieved_docs
            )
            
            # Format retrieval context
            retrieval_context = self.rag_engine.format_retrieval_context(similar_templates)

            # Generate template with retries
            max_retries = self.settings.template_generation.max_retries
            generated_template = None
            
            last_validation_result = None
            
            for attempt in range(max_retries):
                try:
                    generated_template = await self._generate_template_content(request, retrieval_context)
                    
                    # Validate the generated template
                    if self.settings.template_generation.validation_required:
                        validation_result = await self.nuclei_runner.validate_template(generated_template)
                        last_validation_result = validation_result
                        
                        if validation_result.is_valid:
                            break
                        else:
                            if attempt < max_retries - 1:
                                # Try to improve the template based on validation errors
                                generated_template = await self._refine_template(
                                    generated_template, 
                                    validation_result, 
                                    request
                                )
                            else:
                                # Last attempt failed, set template to None
                                generated_template = None
                    else:
                        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
                        last_validation_result = validation_result
                        break
                        
                except Exception as e:
                    logger.error(f"Template generation attempt {attempt + 1} failed: {e}")
                    last_validation_result = ValidationResult(
                        is_valid=False, 
                        errors=[f"Generation attempt {attempt + 1} failed: {str(e)}"], 
                        warnings=[]
                    )
                    if attempt == max_retries - 1:
                        generated_template = None
            
            # Check if we have a valid template
            if not generated_template or (last_validation_result and not last_validation_result.is_valid):
                error_msg = "Failed to generate valid template after all retries"
                if last_validation_result:
                    error_msg += f". Last validation errors: {last_validation_result.errors}"
                raise Exception(error_msg)
            
            # Extract template ID
            template_id = self._extract_template_id(generated_template)
            
            # Create response
            response = TemplateGenerationResponse(
                success=True,
                template_id=template_id,
                generated_template=generated_template,             
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Template generation failed: {e}")
            return TemplateGenerationResponse(
                success=False,
                template_id="failed_generation",
                generated_template=""
            )
    
    async def _generate_template_content(
        self, 
        request: TemplateGenerationRequest, 
        retrieval_context: str
    ) -> str:
        """Generate template content using LLM"""
        # Format user prompt
        user_prompt = self.user_prompt_template.format(
            prompt=request.prompt,
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
        
        # Validate YAML syntax before returning
        self._validate_yaml_syntax(yaml_content)
        
        return yaml_content
    
    def _extract_yaml_content(self, content: str) -> str:
        """Extract YAML content from LLM response"""
        lines = content.split('\n')
        yaml_lines = []
        in_yaml_block = False
        found_yaml_block = False
        
        # First, try to find YAML code blocks
        for line in lines:
            if line.strip().startswith('```yaml') or line.strip().startswith('```yml'):
                in_yaml_block = True
                found_yaml_block = True
                continue
            elif line.strip() == '```' and in_yaml_block:
                in_yaml_block = False
                break
            elif in_yaml_block:
                yaml_lines.append(line)
        
        # If YAML block found, use it
        if found_yaml_block and yaml_lines:
            yaml_content = '\n'.join(yaml_lines).strip()
        else:
            # No YAML block found, try to extract YAML from the entire content
            # Look for lines that start with YAML keys (id:, info:, requests:, etc.)
            yaml_started = False
            for line in lines:
                line_stripped = line.strip()
                # Skip markdown headers, explanations, etc.
                if line_stripped.startswith('#') and not yaml_started:
                    continue
                if line_stripped.startswith('**') or line_stripped.startswith('*') and not yaml_started:
                    continue
                if line_stripped.startswith('```') and not line_stripped.startswith('```yaml'):
                    continue
                    
                # Check for YAML structure start
                if line_stripped.startswith(('id:', 'info:', 'variables:', 'requests:', 'http:', 'network:', 'file:')):
                    yaml_started = True
                    
                if yaml_started:
                    yaml_lines.append(line)
            
            yaml_content = '\n'.join(yaml_lines).strip()
        
        # If still no content, use the entire response as fallback
        if not yaml_content:
            yaml_content = content.strip()
        
        return yaml_content
    
    def _validate_yaml_syntax(self, yaml_content: str) -> None:
        """Validate YAML syntax before nuclei validation"""
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            # Save problematic YAML to temp file for debugging
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(yaml_content)
                logger.error(f"Problematic YAML saved to: {f.name}")
            raise ValueError(f"Generated content is not valid YAML: {e}")
    
    def _extract_template_id(self, template_content: str) -> str:
        """Extract template ID from generated content"""
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
        """Refine template based on validation errors"""
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

Please provide a corrected version of the template that addresses these validation issues while maintaining the original functionality for detecting: {original_request.prompt}
"""
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=refinement_prompt)
        ]
        
        response = await self.llm.agenerate([messages])
        refined_content = response.generations[0][0].text.strip()
        
        refined_yaml = self._extract_yaml_content(refined_content)
        
        # Debug: Log refined YAML
        logger.debug(f"Refined YAML content:\n{refined_yaml}")
        
        return refined_yaml