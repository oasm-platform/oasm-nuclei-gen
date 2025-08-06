"""
Nuclei runner wrapper for template validation and execution
"""
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

from app.models.template import ValidationResult


logger = logging.getLogger(__name__)


class NucleiRunner:
    def __init__(self, config: Optional[Dict[str, str]] = None):
        self.config = config or {}
        self.nuclei_binary = self.config.get("binary_path", "nuclei")
        self.timeout = self.config.get("timeout", 30)
        self.validate_args = self.config.get("validate_args", ["--validate", "--verbose"])
    
    async def validate_template(self, template_content: str, template_id: Optional[str] = None) -> ValidationResult:
        template_id = template_id or "temp_template"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write(template_content)
            temp_file_path = temp_file.name
        
        try:
            return await self._run_validation(temp_file_path, template_id)
        finally:
            Path(temp_file_path).unlink(missing_ok=True)
    
    async def validate_template_file(self, template_path: Path) -> ValidationResult:
        if not template_path.exists():
            return ValidationResult(
                is_valid=False,
                errors=[f"Template file not found: {template_path}"],
                warnings=[]
            )
        
        return await self._run_validation(str(template_path), template_path.stem)
    
    async def _run_validation(self, template_path: str, template_id: str) -> ValidationResult:
        cmd = [self.nuclei_binary] + self.validate_args + ["-t", template_path]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Nuclei validation timed out after {self.timeout} seconds"],
                    warnings=[]
                )
            
            return self._parse_validation_output(
                stdout.decode(),
                stderr.decode(),
                process.returncode,
                template_id
            )
            
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                errors=[f"Nuclei binary not found: {self.nuclei_binary}"],
                warnings=[]
            )
        except Exception as e:
            logger.error(f"Error running nuclei validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Unexpected error during validation: {str(e)}"],
                warnings=[]
            )
    
    def _parse_validation_output(
        self, 
        stdout: str, 
        stderr: str, 
        return_code: int, 
        template_id: str
    ) -> ValidationResult:
        errors = []
        warnings = []
        
        # Parse stderr for errors and warnings
        for line in stderr.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            line_lower = line.lower()
            if any(error_keyword in line_lower for error_keyword in ['error', 'invalid', 'failed', 'fatal']):
                errors.append(line)
            elif any(warning_keyword in line_lower for warning_keyword in ['warning', 'warn']):
                warnings.append(line)
            elif 'could not' in line_lower or 'unable to' in line_lower:
                errors.append(line)
        
        # Parse stdout for additional information
        for line in stdout.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            line_lower = line.lower()
            if 'loaded' in line_lower and 'template' in line_lower:
                # Template loaded successfully
                continue
            elif any(error_keyword in line_lower for error_keyword in ['error', 'invalid']):
                errors.append(line)
        
        # Determine if template is valid based on return code and parsed output
        is_valid = return_code == 0 and not errors
        
        # If no specific errors found but return code is non-zero, add generic error
        if not is_valid and not errors and return_code != 0:
            errors.append(f"Template validation failed with return code {return_code}")
        
        logger.info(f"Template {template_id} validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            logger.warning(f"Validation errors for {template_id}: {errors}")
        if warnings:
            logger.info(f"Validation warnings for {template_id}: {warnings}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    async def validate_yaml_syntax(self, template_content: str) -> ValidationResult:
        try:
            yaml.safe_load(template_content)
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"YAML syntax error: {str(e)}"],
                warnings=[]
            )
    
    async def get_nuclei_version(self) -> Optional[str]:
        try:
            process = await asyncio.create_subprocess_exec(
                self.nuclei_binary, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10
            )
            
            version_output = stdout.decode() + stderr.decode()
            for line in version_output.split('\n'):
                if 'nuclei' in line.lower() and any(char.isdigit() for char in line):
                    return line.strip()
            
            return version_output.strip() if version_output.strip() else None
            
        except Exception as e:
            logger.error(f"Error getting Nuclei version: {e}")
            return None
    
    async def check_nuclei_available(self) -> bool:
        version = await self.get_nuclei_version()
        return version is not None
    
    async def run_template(
        self, 
        template_path: str, 
        target: str, 
        additional_args: Optional[List[str]] = None
    ) -> Tuple[bool, str, str]:
        additional_args = additional_args or []
        cmd = [self.nuclei_binary, "-t", template_path, "-target", target] + additional_args
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout * 2  # Allow more time for actual execution
            )
            
            return (
                process.returncode == 0,
                stdout.decode(),
                stderr.decode()
            )
            
        except Exception as e:
            logger.error(f"Error running template: {e}")
            return False, "", str(e)
