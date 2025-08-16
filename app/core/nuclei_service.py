"""
Nuclei Template Service - Simplified service
"""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import yaml

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config_service import ConfigService
from app.core.rag_engine import RAGEngine
from app.core.models import TemplateGenerationRequest, TemplateGenerationResponse


logger = logging.getLogger(__name__)


class NucleiTemplateService:
    """Nuclei Template Service"""
    
    def __init__(self):
        self.settings = ConfigService.get_settings()
        self.rag_engine = RAGEngine()
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

    
    async def generate_template(self, request: TemplateGenerationRequest) -> TemplateGenerationResponse:
        """Generate a Nuclei template"""        
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

            # Generate template
            generated_template = await self._generate_template_content(request, retrieval_context)
            
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
    
